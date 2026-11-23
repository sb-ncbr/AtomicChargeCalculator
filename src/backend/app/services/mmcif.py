import os
import pathlib

from gemmi import cif

from api.v1.constants import CHARGES_OUTPUT_EXTENSION
from models.calculation import CalculationResultDto

from services.io import IOService
from services.logging.base import LoggerBase


CHARGES_DICTIONARY_V10_LOCATION = (
    "https://sb-ncbr.github.io/charges-schema/schemas/mmcif_charges_v10.dic"
)


class MmCIFService:
    """Service for handling mmCIF file operations."""

    def __init__(self, logger: LoggerBase, io: IOService):
        self.logger = logger
        self.io = io

    def write_to_mmcif(
        self, user_id: str | None, computation_id: str, calculations: list[CalculationResultDto]
    ) -> dict:
        """Write charges to mmcif files with names corresponding to the input molecules.

        Args:
            data (dict): Data to write
            calculations (list[ChargeCalculationResult]): List of calculations to write.

        Returns:
            dict: Dictionary with "molecules" and "configs" keys.
        """

        data = self._transform_calculation_data(calculations)

        configs = data["configs"]
        molecules = list(data["molecules"])
        for molecule in molecules:
            self._write_molecule_to_mmcif(user_id, computation_id, molecule, data)

        return {"molecules": molecules, "configs": configs}

    def get_molecule_mmcif(self, path: str, molecule: str | None) -> str:
        """Returns a mmcif file for the provided molecule in the provided computation.

        Args:
            computation_id (str): Computation id.
            molecule (str | None): Molecule name. Will return the first one if not provided.

        Raises:
            FileNotFoundError: If the provided path or molecule does not exist.

        Returns:
            str: Path to the mmcif file.
        """

        if not self.io.path_exists(path):
            raise FileNotFoundError()

        if molecule is None:
            molecules = [
                file for file in self.io.listdir(path) if file.endswith(CHARGES_OUTPUT_EXTENSION)
            ]

            if len(molecules) == 0:
                raise FileNotFoundError()

            return str(pathlib.Path(path) / molecules[0])

        path = str(pathlib.Path(path) / f"{molecule.lower()}{CHARGES_OUTPUT_EXTENSION}")
        if not self.io.path_exists(path):
            raise FileNotFoundError()

        return path

    def _transform_calculation_data(self, calculations: list[CalculationResultDto]) -> dict:
        """Transforms input data to a 'molecule-focused' format"""
        transformed = {
            "molecules": {},
            "configs": [
                {
                    "method": calculation.config.method,
                    "parameters": calculation.config.parameters,
                }
                for calculation in calculations
            ],
        }

        # A configuration may have no charges for a molecule, when its calculation failed,
        # so each molecule lists the configurations it has charges of.
        for config_index, calculation in enumerate(calculations):
            for calculation_part in calculation.calculations:
                for molecule, charges in calculation_part.charges.items():
                    if molecule not in transformed["molecules"]:
                        transformed["molecules"][molecule] = {"charges": []}

                    transformed["molecules"][molecule]["charges"].append(
                        (config_index, charges)
                    )

        return transformed

    def _write_molecule_to_mmcif(
        self, user_id: str | None, computation_id: str, molecule: str, data: dict
    ) -> str:
        configs = data["configs"]
        charges = data["molecules"][molecule]["charges"]

        charges_path = self.io.get_charges_path(computation_id, user_id)
        output_file_path = os.path.join(
            charges_path, f"{molecule.lower()}{CHARGES_OUTPUT_EXTENSION}"
        )

        document = cif.read_file(output_file_path)
        block = document.sole_block()

        sb_ncbr_partial_atomic_charges_meta_prefix = "_sb_ncbr_partial_atomic_charges_meta."
        sb_ncbr_partial_atomic_charges_prefix = "_sb_ncbr_partial_atomic_charges."
        sb_ncbr_partial_atomic_charges_meta_attributes = ["id", "type", "method"]
        sb_ncbr_partial_atomic_charges_attributes = ["type_id", "atom_id", "charge"]

        # The charge engine wrote one charge set; its rows name the _atom_site.id of each
        # charged atom, in the order of the charges. The engine keeps the IDs of an uploaded
        # structure, so they are not always the atom positions.
        engine_rows = block.find(sb_ncbr_partial_atomic_charges_prefix, ["type_id", "atom_id"])
        first_type_id = engine_rows[0][0] if len(engine_rows) else None
        atom_ids = [row[1] for row in engine_rows if row[0] == first_type_id]

        block.find_mmcif_category(sb_ncbr_partial_atomic_charges_meta_prefix).erase()
        block.find_mmcif_category(sb_ncbr_partial_atomic_charges_prefix).erase()

        metadata_loop = block.init_loop(
            sb_ncbr_partial_atomic_charges_meta_prefix,
            sb_ncbr_partial_atomic_charges_meta_attributes,
        )

        # Charge sets are numbered from 1 without gaps, as ACC's viewer requires.
        for type_id, (config_index, _) in enumerate(charges, start=1):
            method_name = configs[config_index]["method"]
            parameters_name = configs[config_index]["parameters"]
            metadata_loop.add_row(
                [f"{type_id}", "'empirical'", f"'{method_name}/{parameters_name}'"]
            )

        charges_loop = block.init_loop(
            sb_ncbr_partial_atomic_charges_prefix, sb_ncbr_partial_atomic_charges_attributes
        )

        for type_id, (_, molecule_charges) in enumerate(charges, start=1):
            if len(molecule_charges) != len(atom_ids):
                raise ValueError(
                    f"Molecule '{molecule}' has {len(atom_ids)} charged atoms in its mmCIF file "
                    f"but {len(molecule_charges)} charges for charge set {type_id}."
                )
            for atom_id, charge in zip(atom_ids, molecule_charges):
                charges_loop.add_row([f"{type_id}", atom_id, f"{charge: .4f}"])

        self._declare_charges_dictionary(block)
        block.write_file(output_file_path)

    @staticmethod
    def _declare_charges_dictionary(block: cif.Block) -> None:
        """Declares version 1.0 of the charges dictionary, whose layout ACC writes.

        ChargeFW writes version 1.1, which has the parameter set as a separate item; the
        Mol* extension and ACC's viewer read "method/parameters" from the method item.
        """

        audit_conform = block.get_mmcif_category("_audit_conform.", raw=True)
        existing = list(audit_conform)
        # CIF tags are case-insensitive; the file's own spelling is kept.
        spelling = {tag.lower(): tag for tag in existing}
        dict_name, dict_version, dict_location = (
            spelling.get(tag, tag) for tag in ("dict_name", "dict_version", "dict_location")
        )
        tags = existing + [
            tag for tag in (dict_name, dict_version, dict_location) if tag not in existing
        ]
        names = [cif.as_string(name) for name in audit_conform.get(dict_name, [])]
        row_count = len(audit_conform[existing[0]]) if existing else 0
        rows = [
            {tag: audit_conform[tag][row] for tag in existing}
            for row in range(row_count)
            if not (row < len(names) and names[row].startswith("mmcif_charges_"))
        ]
        rows.append(
            {
                dict_name: "mmcif_charges_v10.dic",
                dict_version: "1.0",
                dict_location: CHARGES_DICTIONARY_V10_LOCATION,
            }
        )
        block.set_mmcif_category(
            "_audit_conform.",
            {tag: [row.get(tag, "?") for row in rows] for tag in tags},
            raw=True,
        )
