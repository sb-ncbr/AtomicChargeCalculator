"""ChargeFW 3 integration through its Python package."""

import functools
import os
import tempfile
import threading
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import chargefw
import chargefw_ccd
import gemmi
import numpy as np
from integrations.chargefw.base import (
    ATOM_IDS_UNSUPPORTED,
    NOT_APPLICABLE,
    OUT_OF_MEMORY,
    PARAMETER_SET_REQUIRED,
    CalculatedCharges,
    ChargeCalculationError,
    ChargeEngine,
    MoleculeReadError,
)
from models.issue import IssueDto, IssueSource
from models.method import Method
from models.parameters import Parameters

# Methods of type "other": they return the formal charges and zeros, they are not charge
# models.
NON_MODEL_METHODS = frozenset({"formal", "dummy"})


# ACC's upload extensions and the ChargeFW reader for each.
INPUT_FORMATS = {
    ".sdf": "sdf",
    ".mol2": "mol2",
    ".pdb": "pdb",
    ".cif": "mmcif",
    ".mmcif": "mmcif",
}
STRUCTURE_FORMATS = frozenset({"pdb", "mmcif"})

# Threads of one calculation. Calculations also run side by side in ACC's own thread pool,
# so each gets only two; they speed up the full calculation of a large structure, and cutoff
# and cover. ChargeFW chooses the execution: expensive methods such as EEM and SQE+qp run
# in full up to 20,000 atoms in the largest molecule, with cutoff up to 80,000, and with
# cover above.
THREADS = 2


# What users see when ChargeFW runs out of memory; it raises MemoryError then.
TOO_LARGE = "The structure is too large for the memory of this server."

# Longest molecule name ACC uses.
MAX_NAME_LENGTH = 80

# Largest _atom_site.id that ChargeFW's mmCIF writer refers a charge to.
MAX_ATOM_ID = 2**31 - 1

# Charges beyond this many e are outside the range of the mmCIF charge dictionary.
MAX_MMCIF_CHARGE = 10


@dataclass(frozen=True)
class ChargeFWMolecules:
    """Molecules read from one file, with the parameter matching ACC's settings ask for.

    ChargeFW takes the matching with each assessment and calculation.
    """

    collection: chargefw.MoleculeCollection
    parameter_matching: Literal["strict", "permissive"]
    file_path: str
    input_format: str


def _input_format(file_path: str) -> str:
    extension = Path(file_path).suffix.lower()
    try:
        return INPUT_FORMATS[extension]
    except KeyError:
        raise ValueError(f"Unsupported file type '{extension}'.") from None


_components_lock = threading.Lock()


@functools.cache
def _load_components() -> chargefw.io.ComponentDictionary:
    return chargefw.io.ComponentDictionary(chargefw_ccd.path())


def _components() -> chargefw.io.ComponentDictionary:
    """The wwPDB Chemical Component Dictionary of the chargefw-ccd package.

    It gives the bonds of ligands and modified residues, which ChargeFW's residue templates
    do not cover and which PDB archive files leave out. It takes about 0.4 s and 40 MB, so
    each process loads it once, on its first PDB or mmCIF file.
    """

    with _components_lock:
        return _load_components()


def _selection(read_hetatm: bool, ignore_water: bool) -> str:
    """ChargeFW's selection for ACC's settings.

    Without HETATM records ChargeFW keeps the polymers, modified residues included: it
    selects by the entities of the file, not by the record type.
    """

    if not read_hetatm:
        return "polymers"
    return "polymers-and-ligands" if ignore_water else "all"


def molecule_names(collection: chargefw.MoleculeCollection) -> list[str]:
    """ACC's molecule names, which it uses as keys, file names, and URL parameters.

    Every byte other than an ASCII letter or digit becomes "_", the name is cut at 80
    characters, and repeated names get "_0", "_1", ... ChargeFW keeps names as written,
    such as "2,4-dinitrophenol", which ACC names "2_4_dinitrophenol".

    Names are repeated whatever their case, as the viewer files have the name in lower case.
    """

    names: list[str] = []
    used: set[str] = set()
    for molecule in collection:
        name = "".join(
            chr(byte) if chr(byte).isascii() and chr(byte).isalnum() else "_"
            for byte in molecule.name.encode()
        )[:MAX_NAME_LENGTH]

        unique, count = name, 0
        while unique.lower() in used:
            unique = f"{name}_{count}"
            count += 1

        used.add(unique.lower())
        names.append(unique)
    return names


def _check_atom_ids(collection: chargefw.MoleculeCollection) -> None:
    """Refuses structures whose atom IDs the charges in the viewer file cannot refer to.

    The charge dictionary refers to _atom_site.id as a positive integer, and ChargeFW keeps
    the IDs of the input, so it cannot add charges to atoms with IDs such as "Osite" or "01",
    or with IDs above the largest one its writer takes.
    """

    for molecule in collection:
        for atom_id in molecule.atom_ids:
            text = str(atom_id)
            if not (text.isascii() and text.isdigit() and text[0] != "0"):
                problem = "is not a positive integer"
            elif int(text) > MAX_ATOM_ID:
                problem = f"is above {MAX_ATOM_ID}"
            else:
                continue
            raise ChargeCalculationError(
                f"Atom ID '{text}' {problem}. ACC can show charges only of structures whose "
                f"atom IDs (_atom_site.id) are positive integers up to {MAX_ATOM_ID}.",
                kind=ATOM_IDS_UNSUPPORTED,
            )


def _check_structure(molecules: ChargeFWMolecules) -> None:
    """Refuses structures that ACC cannot show the charges of, whatever the method."""

    if molecules.input_format == "mmcif":
        # A PDB input is converted to mmCIF with sites numbered by Gemmi.
        _check_atom_ids(molecules.collection)


def _issue(issue, source: IssueSource, names: list[str], molecule_index: int | None = None) -> IssueDto:
    """ChargeFW's issue with its kind, ACC's name of the molecule, and the atoms it names."""

    if molecule_index is None:
        molecule_index = getattr(issue, "molecule_index", None)
    return IssueDto(
        kind=issue.kind,
        message=issue.message,
        source=source,
        molecule=names[molecule_index] if molecule_index is not None else None,
        # A NumPy array, or None when the issue names no atoms.
        atom_indices=[] if issue.atom_indices is None else [int(i) for i in issue.atom_indices],
    )


def _config_issue(method: str, parameters: str | None) -> tuple[str, str] | None:
    """Why ACC does not calculate the method with the parameter set, as a kind and a message.

    The kinds are those of ChargeFW's RequestError for the same request, except that ACC
    also requires a parameter set for a method that has some.
    """

    if method not in chargefw.methods:
        return "unknown_method", f"Method '{method}' is not available."

    parameter_sets = chargefw.methods[method].parameter_sets
    if parameters is None:
        if len(parameter_sets) > 0:
            # Without a named set ChargeFW would choose one, and ACC would record the
            # calculation without it.
            return PARAMETER_SET_REQUIRED, f"Method {method} requires parameters."
        return None

    if len(parameter_sets) == 0:
        return "incompatible_parameter_set", f"Method {method} has no parameters."
    if parameters in parameter_sets:
        return None

    # A set of another method is known to ChargeFW.
    known = parameters in chargefw.parameter_sets
    return (
        "incompatible_parameter_set" if known else "unknown_parameter_set",
        f"Parameters '{parameters}' are not available for method {method}.",
    )


def _output_issue(error: chargefw.OutputError, names: list[str]) -> IssueDto:
    """ChargeFW's refusal to write a result, as an issue of the molecule and atoms it names."""

    return IssueDto(
        kind=error.kind,
        message=error.reason,
        source="output",
        molecule=names[error.molecule_index] if error.molecule_index is not None else None,
        atom_indices=[int(i) for i in error.atom_indices],
    )


def _sentence(text: str) -> str:
    """ChargeFW's lower-case text as a sentence; a first word such as "mmCIF" stays."""

    first = text.split(" ", 1)[0]
    if first[1:] == first[1:].lower():
        text = text[:1].upper() + text[1:]
    return text if text.endswith(".") else f"{text}."


def _output_reason(
    error: chargefw.OutputError,
    charge_warnings: list[IssueDto],
    molecules: ChargeFWMolecules,
    names: list[str],
    charges: list[np.ndarray],
) -> str:
    """Why the viewer file of a calculation cannot be written, for users.

    Charges beyond the range of the mmCIF dictionary mostly come with ChargeFW's warning that
    a charge is far from its formal charge, which names the atom and says what to do; the
    range alone does not. The warning must be about the molecule that cannot be written:
    other molecules may have charges that are far off but within the range. And that
    molecule must have a charge beyond the range: the file may be refused for another value.
    """

    index = error.molecule_index
    if (
        error.kind != "unrepresentable"
        or index is None
        or not np.any(np.abs(charges[index]) > MAX_MMCIF_CHARGE)
    ):
        return _reason(error.reason, index, molecules.collection)

    molecule = names[index]
    out_of_range = next(
        (
            issue
            for issue in charge_warnings
            if issue.kind == "charge_out_of_range" and issue.molecule == molecule
        ),
        None,
    )
    if out_of_range is None:
        return _reason(error.reason, index, molecules.collection)

    text = _sentence(out_of_range.message)
    if len(molecules.collection) > 1 and out_of_range.molecule is not None:
        text = f"{out_of_range.molecule}: {text}"
    return f"{text} ACC cannot show charges beyond ±10 e."


def _read_error(error: chargefw.ParseError) -> MoleculeReadError:
    """ChargeFW's refusal of a file with its kind, located by line and record.

    The message of the error starts with the source, the path of the stored upload, which
    users do not need to see.
    """

    where = []
    if error.line is not None:
        where.append(f"line {error.line}")
    if error.record_index is not None:
        name = "" if error.record_id in (None, "") else f" ('{error.record_id}')"
        where.append(f"record {error.record_index + 1}{name}")
    message = f"{', '.join(where)}: {error.reason}" if where else error.reason
    return MoleculeReadError(_sentence(message), kind=error.kind)


def _reason(
    message: str, molecule_index: int | None, collection: chargefw.MoleculeCollection
) -> str:
    """ChargeFW's reason as a sentence, naming the molecule when the file has several.

    ChargeFW gives the molecule and conformer as fields, not in the message; ACC reads only the
    first model, so the conformer is not named.
    """

    text = _sentence(message)
    if molecule_index is not None and len(collection) > 1:
        text = f"{molecule_names(collection)[molecule_index]}: {text}"
    return text


def output_stem(file_path: str, method: str, parameters: str | None) -> str:
    """The name of the TXT, PQR, and MOL2 outputs, without their extension.

    It is the name ChargeFW2 gave them, which ACC keeps for its downloads.
    """

    path = Path(file_path)
    return f"{path.stem}-{method}-{parameters or 'None'}{path.suffix}"


def _txt(names: list[str], charges: list[np.ndarray]) -> str:
    """The TXT download: the name in upper case, then the charges with five decimals.

    It is the format of ChargeFW2, which ACC keeps for its downloads.
    """

    return "".join(
        f"{name.upper()}\n{' '.join(f'{value:.5f}' for value in values)}\n"
        for name, values in zip(names, charges, strict=True)
    )


def _method(method: chargefw.Method) -> Method:
    if method.id in NON_MODEL_METHODS:
        method_type = "other"
    else:
        method_type = "3D" if method.requires_coordinates else "2D"

    return Method(
        internal_name=method.id,
        name=method.name,
        full_name=method.full_name,
        publication=method.publication or None,
        type=method_type,
        has_parameters=len(method.parameter_sets) > 0,
    )


def _parameters(parameter_set: chargefw.ParameterSet) -> Parameters:
    return Parameters(
        internal_name=parameter_set.id,
        full_name=parameter_set.name,
        method=parameter_set.method.id,
        publication=parameter_set.publication,
        notes=parameter_set.notes,
    )


class ChargeFWLocal(ChargeEngine):
    """Calculates charges with the ChargeFW 3 Python package."""

    def molecules(
        self,
        file_path: str,
        read_hetatm: bool = True,
        ignore_water: bool = False,
        permissive_types: bool = True,
    ) -> ChargeFWMolecules:
        input_format = _input_format(file_path)
        options = {}
        if input_format in STRUCTURE_FORMATS:
            # Only the first model is read.
            options = {
                "selection": _selection(read_hetatm, ignore_water),
                "conformers": "first",
                "components": _components(),
            }

        try:
            collection = chargefw.io.read(file_path, format=input_format, **options)
        except chargefw.ParseError as e:
            raise _read_error(e) from e
        except MemoryError as e:
            raise MoleculeReadError(TOO_LARGE, kind=OUT_OF_MEMORY) from e

        return ChargeFWMolecules(
            collection=collection,
            parameter_matching="permissive" if permissive_types else "strict",
            file_path=file_path,
            input_format=input_format,
        )

    def info(self, molecules: ChargeFWMolecules) -> dict:
        counts = Counter(
            chargefw.periodic_table[int(number)].symbol
            for molecule in molecules.collection
            for number in molecule.atomic_numbers
        )
        return {
            "total_molecules": len(molecules.collection),
            "total_atoms": sum(molecule.atom_count for molecule in molecules.collection),
            "atom_type_counts": [
                {"symbol": symbol, "count": count} for symbol, count in counts.items()
            ],
        }

    def warnings(self, molecules: ChargeFWMolecules) -> list[IssueDto]:
        """Every import warning of ChargeFW, such as "unbonded_residue_atoms".

        Bonds of ligands and modified residues come from the file, CONECT records of PDB
        files and _chem_comp_bond of mmCIF files, or from the component dictionary. Atoms
        of a residue that is in neither, such as a new ligand, have no bonds.
        """

        names = molecule_names(molecules.collection)
        return [
            _issue(issue, "import", names, index)
            for index, molecule in enumerate(molecules.collection)
            for issue in molecule.import_warnings
        ]

    def get_available_methods(self) -> list[Method]:
        return [_method(method) for method in chargefw.methods.values()]

    def get_available_parameters(self, method: str) -> list[Parameters]:
        return [
            _parameters(parameter_set)
            for parameter_set in chargefw.methods[method].parameter_sets.values()
        ]

    def get_best_parameters(
        self, molecules: ChargeFWMolecules, method: str
    ) -> Parameters | None:
        # As for the suitable methods: no parameters can be calculated with then.
        _check_structure(molecules)

        assessment = chargefw.assess(
            molecules.collection,
            method=method,
            parameter_matching=molecules.parameter_matching,
            threads=THREADS,
        )
        plan = assessment.default_plan
        if plan is None or plan.parameter_set is None:
            return None
        return _parameters(plan.parameter_set)

    def get_suitable_methods(
        self, molecules: ChargeFWMolecules
    ) -> list[tuple[Method, list[Parameters]]]:
        """Applicable methods with their parameter sets, in the order ChargeFW tries them.

        The assessment lists the cutoff and cover variants of a method and parameter set
        as separate plans; each pair is listed once.
        """

        # No method can be calculated then; the reason is known before any calculation.
        _check_structure(molecules)

        assessment = chargefw.assess(
            molecules.collection,
            method_scope="all",
            parameter_matching=molecules.parameter_matching,
            threads=THREADS,
        )

        suitable: dict[str, tuple[Method, list[Parameters]]] = {}
        for plan in assessment.plans:
            _, parameters = suitable.setdefault(
                plan.method.id, (_method(plan.method), [])
            )
            if plan.parameter_set is not None:
                entry = _parameters(plan.parameter_set)
                if entry not in parameters:
                    parameters.append(entry)

        return list(suitable.values())

    def calculate_charges(
        self,
        molecules: ChargeFWMolecules,
        method_name: str,
        parameters_name: str | None = None,
        chg_out_dir: str | None = None,
    ) -> CalculatedCharges:
        """Calculates charges and writes the output files to chg_out_dir.

        Writes "<name>.fw2.cif" for each molecule, and TXT and PQR (structures) or MOL2
        (molecule files) named by the input, method, and parameters.
        A PQR or MOL2 file that ChargeFW cannot write is left out with a warning.
        """

        if (issue := _config_issue(method_name, parameters_name)) is not None:
            kind, message = issue
            raise ChargeCalculationError(message, kind=kind)

        names = molecule_names(molecules.collection)

        _check_structure(molecules)

        try:
            result = chargefw.calculate(
                molecules.collection,
                method=method_name,
                parameter_set=parameters_name,
                parameter_matching=molecules.parameter_matching,
                threads=THREADS,
            )
        except chargefw.RequestError as e:
            # ACC checks the method and parameter set before; ChargeFW checks the rest of
            # the request.
            raise ChargeCalculationError(_sentence(e.reason), kind=e.kind) from e
        except chargefw.NoExecutablePlanError as e:
            # ChargeFW's own message lists several reasons; the first one is enough for the
            # message, and all are kept with their kinds.
            issues = [issue for rejection in e.result.rejections for issue in rejection.issues]
            if not issues:
                raise ChargeCalculationError(
                    "The method does not apply to the molecules.", kind=NOT_APPLICABLE
                ) from e
            raise ChargeCalculationError(
                _reason(issues[0].message, issues[0].molecule_index, molecules.collection),
                kind=issues[0].kind,
                issues=[_issue(issue, "rejection", names) for issue in issues],
            ) from e
        except chargefw.NumericalFailureError as e:
            failure = e.result.failure
            raise ChargeCalculationError(
                _reason(failure.message, failure.molecule_index, molecules.collection),
                kind=failure.kind,
                issues=[_issue(failure, "failure", names)],
            ) from e
        except MemoryError as e:
            raise ChargeCalculationError(TOO_LARGE, kind=OUT_OF_MEMORY) from e

        warnings = [
            _issue(issue, source, names)
            for source, issues in (
                ("input", result.input_warnings),
                ("charge", result.charge_warnings),
                ("plan", result.plan.warnings),
            )
            for issue in issues
        ]

        # Only the first model is read, so each molecule has one set of charges.
        charges = [assignments[0].values for assignments in result.assignments_by_molecule]

        out_dir = Path(chg_out_dir or ".")
        stem = output_stem(molecules.file_path, method_name, parameters_name)
        output_format = "pqr" if molecules.input_format in STRUCTURE_FORMATS else "mol2"

        # The files go to out_dir only when every one of them is written: the download
        # lists every file there, and a calculation that failed must not be in it.
        with tempfile.TemporaryDirectory(dir=out_dir, prefix=".staging-") as staging:
            staged = Path(staging)
            try:
                self._write_viewer_files(result, molecules, names, staged)
            except chargefw.OutputError as e:
                # Such as charges outside the range of the mmCIF dictionary, which ChargeFW
                # may also warn are probably wrong. ACC shows the charges only from these
                # files.
                charge_warnings = [issue for issue in warnings if issue.source == "charge"]
                raise ChargeCalculationError(
                    _output_reason(e, charge_warnings, molecules, names, charges),
                    kind=e.kind,
                    issues=[_output_issue(e, names), *charge_warnings],
                ) from e
            download = staged / f"{stem}.{output_format}"
            try:
                chargefw.io.write(download, result, format=output_format)
            except chargefw.OutputError as e:
                download.unlink(missing_ok=True)
                # Only a download, so the calculation stands without it. PQR cannot hold
                # chain IDs such as "AA" or "1" of large structures, which readers such as
                # APBS misread.
                warnings.append(_output_issue(e, names))
            (staged / f"{stem}.txt").write_text(_txt(names, charges))
            for file in staged.iterdir():
                file.replace(out_dir / file.name)

        return CalculatedCharges(
            charges={name: values.tolist() for name, values in zip(names, charges, strict=True)},
            warnings=warnings,
        )

    def _write_viewer_files(
        self,
        result: chargefw.CalculationResult,
        molecules: ChargeFWMolecules,
        names: list[str],
        out_dir: Path,
    ) -> None:
        """Writes "<name>.fw2.cif" for each molecule, the file ACC shows in Mol* and offers
        for download.

        For PDB and mmCIF input, it is the uploaded structure with the charges added:
        other models, assemblies, and secondary structure stay. Molecule
        files get the structure ChargeFW writes, with bond orders for Mol*.
        """

        if molecules.input_format not in STRUCTURE_FORMATS:
            document = gemmi.cif.read_string(chargefw.io.dumps(result, format="mmcif"))
            blocks = list(document)
        else:
            # Configurations of one input run at the same time; each needs its own file.
            descriptor, name = tempfile.mkstemp(
                dir=out_dir, prefix=f".{Path(molecules.file_path).name}.", suffix=".annotated.cif"
            )
            os.close(descriptor)
            annotated = Path(name)
            try:
                # The upload may be an ACC download that has charges already.
                chargefw.io.annotate(annotated, result, if_exists="replace")
                document = gemmi.cif.read(str(annotated))
            finally:
                annotated.unlink(missing_ok=True)

            # Blocks without coordinates are copied unchanged and have no charges.
            blocks = [
                block
                for block in document
                if block.find_values("_sb_ncbr_partial_atomic_charges.atom_id")
            ]
            for block in blocks:
                prepare_structure_for_viewer(block)

        for block, name in zip(blocks, names, strict=True):
            block.write_file(str(out_dir / f"{name.lower()}.fw2.cif"))


def prepare_structure_for_viewer(block: gemmi.cif.Block) -> None:
    """Removes what ACC's viewer cannot show or Mol* shows worse.

    - Atom rows of the first model without a charge: other alternate locations, water or
      HETATM records left out by the settings. ACC's viewer requires a charge for each atom
      of the model it shows. Other models are kept.
    - `_chem_comp`: with it, Mol* shows the polymer of a PDB upload without cartoon and
      modified residues as ball-and-stick.
    """

    # IDs are compared as CIF values: a quoted '14' is the charged atom 14, a water 014 is
    # not. The rows are written back as they were read.
    charged = {
        gemmi.cif.as_string(atom_id)
        for atom_id in block.find_values("_sb_ncbr_partial_atomic_charges.atom_id")
    }
    atom_site = block.get_mmcif_category("_atom_site.", raw=True)
    # CIF tags are case-insensitive; the file's own spelling is written back.
    tags = {tag.lower(): tag for tag in atom_site}
    ids = atom_site[tags["id"]]
    # Model numbers are compared as numbers: 01 is model 1.
    models = [
        _model_number(model) for model in atom_site.get(tags.get("pdbx_pdb_model_num", ""), [])
    ]
    first_model = models[0] if models else None

    keep = [
        row
        for row, atom_id in enumerate(ids)
        # IDs of other models are not read: they need not be integers.
        if (models and models[row] != first_model) or gemmi.cif.as_string(atom_id) in charged
    ]
    if len(keep) < len(ids):
        block.set_mmcif_category(
            "_atom_site.",
            {tag: [values[row] for row in keep] for tag, values in atom_site.items()},
            raw=True,
        )
        _remove_rows_of_other_atoms(
            block, "_atom_site_anisotrop.", {gemmi.cif.as_string(ids[row]) for row in keep}
        )

    block.find_mmcif_category("_chem_comp.").erase()


def _model_number(value: str) -> int | str:
    """A model number as ChargeFW reads it: 1, 01, and +1 are one model."""

    text = gemmi.cif.as_string(value)
    try:
        return int(text)
    except ValueError:
        return text


def _remove_rows_of_other_atoms(block: gemmi.cif.Block, prefix: str, atom_ids: set[str]) -> None:
    """Removes the rows of a category that refer, by their id, to atoms the file no longer has."""

    category = block.get_mmcif_category(prefix, raw=True)
    tags = {tag.lower(): tag for tag in category}
    if "id" not in tags:
        return
    ids = category[tags["id"]]
    keep = [row for row, atom_id in enumerate(ids) if gemmi.cif.as_string(atom_id) in atom_ids]
    if len(keep) == len(ids):
        return
    if not keep:
        block.find_mmcif_category(prefix).erase()
        return
    block.set_mmcif_category(
        prefix, {tag: [values[row] for row in keep] for tag, values in category.items()}, raw=True
    )
