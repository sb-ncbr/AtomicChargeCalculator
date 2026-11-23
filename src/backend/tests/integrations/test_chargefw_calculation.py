import shutil
from pathlib import Path

import chargefw
import gemmi
import pytest

from integrations.chargefw.base import ChargeCalculationError
from app.integrations.chargefw.chargefw import ChargeFWLocal, molecule_names

DATA = Path(__file__).parent.parent / "data" / "integrations"
METHOD, PARAMETERS = "sqeqp", "SQEqp_Schindler2021_CCD_gen"

# ChargeFW2's TXT output for the first phenol with SQE+qp and Schindler 2021 (CCD_gen).
DINITROPHENOL_CHARGEFW2 = [
    -0.64491, -0.29083, -0.30515, -0.27775, -0.33729, 0.44103, 0.43448, -0.03617, 0.02959,
    -0.12043, 0.32925, -0.14436, -0.23866, 0.23643, 0.22637, 0.22296, 0.47542,
]  # fmt: skip


@pytest.fixture(scope="module")
def engine():
    return ChargeFWLocal()


@pytest.fixture
def phenols(tmp_path):
    # ACC stores uploads as "<hash>_<name>".
    path = tmp_path / "inputs" / "abc_phenols.sdf"
    path.parent.mkdir()
    shutil.copy(DATA / "phenols.sdf", path)
    return str(path)


def molecule(name: str) -> chargefw.Molecule:
    return chargefw.Molecule(atomic_numbers=[1], name=name)


def test_names_are_ascii_letters_and_digits_cut_and_unique():
    collection = chargefw.MoleculeCollection(
        [
            molecule("2,4-dinitrophenol"),
            molecule("a" * 85),
            molecule("x y"),
            molecule("x-y"),
            molecule("x.y"),
            molecule("Ýx"),
        ]
    )

    assert molecule_names(collection) == [
        "2_4_dinitrophenol",
        "a" * 80,
        "x_y",
        "x_y_0",
        "x_y_1",
        "__x",  # every byte of a non-ASCII character
    ]


def test_names_are_unique_whatever_their_case():
    # ACC writes "<name in lower case>.fw2.cif" for each molecule.
    collection = chargefw.MoleculeCollection([molecule("water"), molecule("Water"), molecule("WATER")])

    assert molecule_names(collection) == ["water", "Water_0", "WATER_1"]


def test_calculation_returns_charges_by_name_and_writes_the_output_files(
    engine, phenols, tmp_path
):
    out = tmp_path / "charges"
    out.mkdir()

    charges = engine.calculate_charges(
        engine.molecules(phenols), METHOD, PARAMETERS, str(out)
    ).charges

    assert list(charges)[:3] == ["2_4_dinitrophenol", "4_nitrophenol", "2_chlorophenol"]
    assert charges["2_4_dinitrophenol"] == pytest.approx(DINITROPHENOL_CHARGEFW2, abs=1e-4)

    stem = f"abc_phenols-{METHOD}-{PARAMETERS}.sdf"
    assert sorted(p.name for p in out.iterdir()) == sorted(
        [f"{stem}.txt", f"{stem}.mol2"] + [f"{name.lower()}.fw2.cif" for name in charges]
    )

    txt = (out / f"{stem}.txt").read_text().splitlines()
    assert len(txt) == 2 * len(charges)
    assert txt[0] == "2_4_DINITROPHENOL"
    assert txt[1] == " ".join(f"{value:.5f}" for value in charges["2_4_dinitrophenol"])

    viewer = gemmi.cif.read(str(out / "2_4_dinitrophenol.fw2.cif")).sole_block()
    assert len(viewer.find_values("_atom_site.id")) == len(DINITROPHENOL_CHARGEFW2)


def test_method_with_parameter_sets_needs_one(engine, phenols, tmp_path):
    with pytest.raises(RuntimeError, match="requires parameters"):
        engine.calculate_charges(engine.molecules(phenols), METHOD, None, str(tmp_path))


def test_running_out_of_memory_says_the_structure_is_too_large(
    engine, phenols, tmp_path, monkeypatch
):
    molecules = engine.molecules(phenols)

    def out_of_memory(*args, **kwargs):
        raise MemoryError

    monkeypatch.setattr(chargefw, "calculate", out_of_memory)
    with pytest.raises(ChargeCalculationError, match="too large") as error:
        engine.calculate_charges(molecules, METHOD, PARAMETERS, str(tmp_path))
    assert error.value.kind == "out_of_memory"


@pytest.fixture
def charged_carbon(tmp_path):
    """A carbon with a formal charge of +12, which EEM leaves at +12 e."""

    path = tmp_path / "abc_charged.sdf"
    path.write_text(
        "charged\n  test\n\n"
        "  1  0  0  0  0  0  0  0  0  0999 V2000\n"
        "    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n"
        "M  CHG  1   1  12\n"
        "M  END\n$$$$\n"
    )
    return str(path)


def test_charges_outside_the_mmcif_range_are_an_error(engine, charged_carbon, tmp_path):
    # GDAC gives such charges for proteins, such as 350 e for 1CBN; ChargeFW does not write
    # them to mmCIF.
    out = tmp_path / "charges"
    out.mkdir()
    with pytest.raises(RuntimeError) as error:
        engine.calculate_charges(
            engine.molecules(charged_carbon), "eem", "EEM_Bult2002_che", str(out)
        )

    assert str(error.value) == "mmCIF charge is outside the dictionary range [-10, 10]."
    assert error.value.kind == "unrepresentable"
    assert [(issue.source, issue.molecule, issue.atom_indices) for issue in error.value.issues][
        0
    ] == ("output", "charged", [0])
    assert list(out.iterdir()) == []


def test_charges_far_from_formal_charges_say_which_atom_and_what_to_do(engine, tmp_path):
    # A carbon and an oxygen 0.315 A apart, which EEM gives about -11.8 e and +11.8 e.
    path = tmp_path / "abc_close.sdf"
    path.write_text(
        "close\n  test\n\n"
        "  2  1  0  0  0  0  0  0  0  0999 V2000\n"
        "    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n"
        "    0.3150    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n"
        "  1  2  2  0\n"
        "M  END\n$$$$\n"
    )
    out = tmp_path / "charges"
    out.mkdir()
    with pytest.raises(ChargeCalculationError) as error:
        engine.calculate_charges(engine.molecules(str(path)), "eem", "EEM_Bult2002_che", str(out))

    message = str(error.value)
    # ChargeFW's warning: both atoms, the furthest named, and what to do.
    assert message.startswith("2 atoms have charges more than 6 e away")
    assert "the charges are probably wrong" in message
    assert message.endswith("ACC cannot show charges beyond \u00b110 e.")
    assert error.value.kind == "unrepresentable"
    assert [issue.kind for issue in error.value.issues] == [
        "unrepresentable",
        "charge_out_of_range",
    ]


def test_charges_out_of_range_name_the_molecule_that_cannot_be_written(engine, tmp_path):
    def record(name: str, distance: str) -> str:
        return (
            f"{name}\n  test\n\n"
            "  2  1  0  0  0  0  0  0  0  0999 V2000\n"
            "    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n"
            f"    {distance}    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n"
            "  1  2  2  0\n"
            "M  END\n$$$$\n"
        )

    # EEM gives "near" about 7.6 e, far from the formal charges but within the range of
    # mmCIF, and "close" about 11.8 e, beyond it. ChargeFW warns about both.
    path = tmp_path / "abc_two.sdf"
    path.write_text(record("near", "0.3400") + record("close", "0.3150"))
    out = tmp_path / "charges"
    out.mkdir()

    with pytest.raises(ChargeCalculationError) as error:
        engine.calculate_charges(engine.molecules(str(path)), "eem", "EEM_Bult2002_che", str(out))

    assert str(error.value).startswith("close: 2 atoms have charges more than 6 e away")
    assert "11.78 e" in str(error.value)


def test_a_file_refused_for_another_value_is_not_blamed_on_its_charges(engine, phenols):
    from types import SimpleNamespace

    import numpy as np

    from app.integrations.chargefw.chargefw import _output_reason
    from models.issue import IssueDto

    molecules = engine.molecules(phenols)
    names = [f"molecule{i}" for i in range(len(molecules.collection))]
    error = SimpleNamespace(
        kind="unrepresentable", reason="atom ID is too large", molecule_index=0, atom_indices=[0]
    )
    far = IssueDto(
        kind="charge_out_of_range", message="2 atoms are far", source="charge", molecule=names[0]
    )
    charges = [np.array([7.6, -7.6])] * len(names)

    # Far from the formal charges, but within the range the file can hold.
    assert _output_reason(error, [far], molecules, names, charges).endswith(
        "Atom ID is too large."
    )
    charges[0] = np.array([11.8, -11.8])
    assert _output_reason(error, [far], molecules, names, charges).endswith(
        "ACC cannot show charges beyond \u00b110 e."
    )


# Two models of water and two ions, with atom IDs that are not positions, the residue
# dictionary, and charges from an earlier calculation.
STRUCTURE_CIF = """data_ions
loop_
_chem_comp.id
_chem_comp.type
HOH non-polymer
MG non-polymer
CA non-polymer
loop_
_atom_site.group_PDB
_atom_site.id
_atom_site.type_symbol
_atom_site.label_atom_id
_atom_site.label_alt_id
_atom_site.label_comp_id
_atom_site.label_asym_id
_atom_site.label_seq_id
_atom_site.Cartn_x
_atom_site.Cartn_y
_atom_site.Cartn_z
_atom_site.pdbx_formal_charge
_atom_site.auth_seq_id
_atom_site.auth_asym_id
_atom_site.label_entity_id
_atom_site.pdbx_PDB_model_num
HETATM 11 O O . HOH W . 0 0 0 0 5 W 1 1
HETATM 12 H H1 . HOH W . 0.96 0 0 0 5 W 1 1
HETATM 13 H H2 . HOH W . -0.24 0.93 0 0 5 W 1 1
HETATM 14 Mg MG . MG I . 0 0 3 2 9 I 2 1
HETATM 15 Ca CA . CA I . 3 0 3 2 10 I 3 1
HETATM 21 O O . HOH W . 0 0 0.1 0 5 W 1 2
HETATM 22 H H1 . HOH W . 0.96 0 0.1 0 5 W 1 2
HETATM 23 H H2 . HOH W . -0.24 0.93 0.1 0 5 W 1 2
HETATM 24 Mg MG . MG I . 0 0 3.1 2 9 I 2 2
HETATM 25 Ca CA . CA I . 3 0 3.1 2 10 I 3 2
loop_
_sb_ncbr_partial_atomic_charges_meta.id
_sb_ncbr_partial_atomic_charges_meta.type
_sb_ncbr_partial_atomic_charges_meta.method
1 empirical 'old/charges'
loop_
_sb_ncbr_partial_atomic_charges.type_id
_sb_ncbr_partial_atomic_charges.atom_id
_sb_ncbr_partial_atomic_charges.charge
1 11 0.1
"""


def test_structure_viewer_file_keeps_the_upload_with_charged_atoms_of_the_first_model(
    engine, tmp_path
):
    path = tmp_path / "abc_ions.cif"
    path.write_text(STRUCTURE_CIF)
    out = tmp_path / "charges"
    out.mkdir()

    molecules = engine.molecules(str(path), selection="polymers-and-ligands")
    calculated = engine.calculate_charges(molecules, "formal", None, str(out))

    assert calculated.charges == {"ions": [2.0, 2.0]}
    block = gemmi.cif.read(str(out / "ions.fw2.cif")).sole_block()
    # Water of the first model is not calculated and goes; the second model stays.
    assert list(block.find_values("_atom_site.id")) == ["14", "15", "21", "22", "23", "24", "25"]
    assert list(block.find_values("_sb_ncbr_partial_atomic_charges.atom_id")) == ["14", "15"]
    assert len(block.find_values("_chem_comp.id")) == 0
    assert sorted(p.name for p in out.iterdir()) == sorted(
        ["ions.fw2.cif", "abc_ions-formal-None.cif.txt", "abc_ions-formal-None.cif.pqr"]
    )


@pytest.mark.parametrize("model", ["01", "+1"])
def test_structure_viewer_file_leaves_no_rows_of_atoms_it_removed(engine, tmp_path, model):
    # Anisotropic displacements of a water of the first model, an ion, and a water of the
    # second model; the first model is numbered 01 or +1 in the rows of its water.
    anisotropic = (
        "loop_\n_atom_site_anisotrop.id\n_atom_site_anisotrop.U[1][1]\n"
        "11 0.1\n14 0.2\n21 0.3\n"
    )
    path = tmp_path / "abc_ions.cif"
    path.write_text(
        STRUCTURE_CIF.replace(" 5 W 1 1\n", f" 5 W 1 {model}\n").replace(
            "loop_\n_sb_ncbr_partial_atomic_charges_meta.id", anisotropic + "loop_\n_sb_ncbr_partial_atomic_charges_meta.id"
        )
    )
    out = tmp_path / "charges"
    out.mkdir()

    molecules = engine.molecules(str(path), selection="polymers-and-ligands")
    engine.calculate_charges(molecules, "formal", None, str(out))

    block = gemmi.cif.read(str(out / "ions.fw2.cif")).sole_block()
    assert list(block.find_values("_atom_site.id")) == ["14", "15", "21", "22", "23", "24", "25"]
    assert list(block.find_values("_atom_site_anisotrop.id")) == ["14", "21"]


def test_a_download_chargefw_cannot_write_is_left_out_with_a_warning(engine, tmp_path):
    # PQR cannot hold a chain ID such as "AA", which large structures such as 9ZNG have.
    path = tmp_path / "abc_ions.cif"
    path.write_text(STRUCTURE_CIF.replace(" 5 W 1 ", " 5 AA 1 "))
    out = tmp_path / "charges"
    out.mkdir()

    calculated = engine.calculate_charges(engine.molecules(str(path)), "formal", None, str(out))

    assert calculated.charges["ions"] == [0.0, 0.0, 0.0, 2.0, 2.0]
    assert sorted(p.name for p in out.iterdir()) == sorted(
        ["ions.fw2.cif", "abc_ions-formal-None.cif.txt"]
    )
    [warning] = [w for w in calculated.warnings if w.source == "output"]
    assert (warning.kind, warning.molecule, warning.atom_indices) == (
        "unrepresentable",
        "ions",
        [0],
    )
    assert "chain ID 'AA'" in warning.message


def test_viewer_file_compares_atom_ids_as_cif_values(engine, tmp_path):
    # A quoted ID is the same value as the unquoted one, "014" is not 14, and IDs of other
    # models are not read.
    path = tmp_path / "abc_ions.cif"
    path.write_text(
        STRUCTURE_CIF.replace("HETATM 14 Mg", "HETATM '14' Mg")
        .replace("HETATM 11 O", "HETATM 014 O")
        .replace("HETATM 21 O", "HETATM X21 O")
    )
    out = tmp_path / "charges"
    out.mkdir()

    molecules = engine.molecules(str(path), selection="polymers-and-ligands")
    engine.calculate_charges(molecules, "formal", None, str(out))

    block = gemmi.cif.read(str(out / "ions.fw2.cif")).sole_block()
    assert list(block.find_values("_atom_site.id")) == ["'14'", "15", "X21", "22", "23", "24", "25"]
    assert list(block.find_values("_sb_ncbr_partial_atomic_charges.atom_id")) == ["14", "15"]


def test_viewer_file_reads_tags_whatever_their_case(engine, tmp_path):
    path = tmp_path / "abc_ions.cif"
    path.write_text(
        STRUCTURE_CIF.replace("_atom_site.id\n", "_atom_site.ID\n").replace(
            "_atom_site.pdbx_PDB_model_num", "_ATOM_SITE.PDBX_PDB_MODEL_NUM"
        )
    )
    out = tmp_path / "charges"
    out.mkdir()

    molecules = engine.molecules(str(path), selection="polymers-and-ligands")
    engine.calculate_charges(molecules, "formal", None, str(out))

    text = (out / "ions.fw2.cif").read_text()
    block = gemmi.cif.read_string(text).sole_block()
    assert list(block.find_values("_atom_site.id")) == ["14", "15", "21", "22", "23", "24", "25"]
    assert "_atom_site.ID\n" in text


def test_a_calculation_whose_files_cannot_all_be_written_leaves_none(
    engine, tmp_path, monkeypatch
):
    import app.integrations.chargefw.chargefw as adapter

    def fail(block):
        raise RuntimeError("Broken viewer file.")

    # The PQR is written before the viewer file fails.
    monkeypatch.setattr(adapter, "prepare_structure_for_viewer", fail)
    path = tmp_path / "abc_ions.cif"
    path.write_text(STRUCTURE_CIF)
    out = tmp_path / "charges"
    out.mkdir()

    with pytest.raises(RuntimeError, match="Broken viewer file"):
        engine.calculate_charges(engine.molecules(str(path)), "formal", None, str(out))
    assert list(out.iterdir()) == []


def test_unknown_method_or_parameters_are_unavailable(engine, phenols, tmp_path):
    molecules = engine.molecules(phenols)

    with pytest.raises(RuntimeError, match="Method 'nope' is not available"):
        engine.calculate_charges(molecules, "nope", None, str(tmp_path))
    with pytest.raises(RuntimeError, match="'SQEqp_unknown' are not available for method sqeqp"):
        engine.calculate_charges(molecules, METHOD, "SQEqp_unknown", str(tmp_path))


def test_configurations_of_one_structure_can_run_at_the_same_time(engine, tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    path = tmp_path / "abc_ions.cif"
    path.write_text(STRUCTURE_CIF)
    out = tmp_path / "charges"
    out.mkdir()

    def calculate(method):
        return engine.calculate_charges(engine.molecules(str(path)), method, None, str(out))

    with ThreadPoolExecutor(8) as executor:
        results = list(executor.map(calculate, ["formal", "dummy"] * 8))

    assert len(results) == 16
    # Every calculation used a temporary file of its own and removed it.
    assert not [p.name for p in out.iterdir() if p.name.startswith(".")]


def test_structure_atom_ids_must_be_positive_integers(engine, tmp_path):
    path = tmp_path / "abc_ions.cif"
    path.write_text(STRUCTURE_CIF.replace("HETATM 11 O", "HETATM Osite O"))

    with pytest.raises(RuntimeError, match="Atom ID 'Osite' is not a positive integer"):
        engine.calculate_charges(engine.molecules(str(path)), "formal", None, str(tmp_path))
    # No method is suitable then, and the reason is known before any calculation.
    with pytest.raises(ChargeCalculationError) as error:
        engine.get_suitable_methods(engine.molecules(str(path)))
    assert error.value.kind == "atom_ids_unsupported"
    with pytest.raises(ChargeCalculationError, match="Atom ID 'Osite'"):
        engine.get_best_parameters(engine.molecules(str(path)), "eem")

    # ChargeFW's writer takes IDs up to 2147483647.
    path.write_text(STRUCTURE_CIF.replace("HETATM 11 O", "HETATM 2147483648 O"))
    with pytest.raises(ChargeCalculationError, match="Atom ID '2147483648' is above 2147483647"):
        engine.get_suitable_methods(engine.molecules(str(path)))
    path.write_text(STRUCTURE_CIF.replace("HETATM 11 O", "HETATM 2147483647 O"))
    engine.calculate_charges(engine.molecules(str(path)), "formal", None, str(tmp_path))


# Water and ammonium; PEOE supports only molecules without a total formal charge.
CHARGED_SDF = """water
  test

  3  2  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
    0.9600    0.0000    0.0000 H   0  0  0  0  0  0  0  0  0  0  0  0
   -0.2400    0.9300    0.0000 H   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0
  1  3  1  0
M  END
$$$$
ammonium
  test

  5  4  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 N   0  0  0  0  0  0  0  0  0  0  0  0
    0.6300    0.6300    0.6300 H   0  0  0  0  0  0  0  0  0  0  0  0
   -0.6300   -0.6300    0.6300 H   0  0  0  0  0  0  0  0  0  0  0  0
   -0.6300    0.6300   -0.6300 H   0  0  0  0  0  0  0  0  0  0  0  0
    0.6300   -0.6300   -0.6300 H   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0
  1  3  1  0
  1  4  1  0
  1  5  1  0
M  CHG  1   1   1
M  END
$$$$
"""


def test_a_method_that_does_not_apply_names_the_molecule_and_reason(engine, tmp_path):
    path = tmp_path / "abc_charged.sdf"
    path.write_text(CHARGED_SDF)

    with pytest.raises(RuntimeError) as error:
        engine.calculate_charges(engine.molecules(str(path)), "peoe", "PEOE_original", str(tmp_path))

    assert str(error.value).startswith("ammonium: The method supports only molecules")
    assert str(error.value).endswith(".")
    # ChargeFW's code of the reason and the molecule it names are kept.
    assert error.value.kind == error.value.issues[0].kind != ""
    assert {(issue.source, issue.molecule) for issue in error.value.issues} == {
        ("rejection", "ammonium")
    }


def test_failures_have_kinds(engine, phenols, tmp_path):
    molecules = engine.molecules(phenols)

    with pytest.raises(RuntimeError) as error:
        engine.calculate_charges(molecules, "nope", None, str(tmp_path))
    assert error.value.kind == "unknown_method"

    broken = tmp_path / "abc_broken.sdf"
    broken.write_text("not a molecule\n")
    with pytest.raises(RuntimeError) as error:
        engine.molecules(str(broken))
    assert error.value.kind == "malformed"


@pytest.mark.parametrize(
    "method, parameters, kind",
    [
        ("nope", None, "unknown_method"),
        (METHOD, None, "parameter_set_required"),
        ("eqeq", "EEM_Baek1991", "incompatible_parameter_set"),
        (METHOD, "EEM_Baek1991", "incompatible_parameter_set"),
        (METHOD, "SQEqp_99_unknown", "unknown_parameter_set"),
        (METHOD, "SQEqp_10_Schindler2021_CCD_gen", "unknown_parameter_set"),
    ],
)
def test_configurations_are_refused_with_the_kinds_of_chargefw(
    engine, phenols, tmp_path, method, parameters, kind
):
    with pytest.raises(RuntimeError) as error:
        engine.calculate_charges(engine.molecules(phenols), method, parameters, str(tmp_path))
    assert error.value.kind == kind


def test_requests_chargefw_refuses_are_failures_with_its_kind(
    engine, phenols, tmp_path, monkeypatch
):
    def calculate(*args, **kwargs):
        raise chargefw.RequestError("cutoff execution requires a radius", kind="invalid_execution")

    monkeypatch.setattr(chargefw, "calculate", calculate)
    with pytest.raises(RuntimeError) as error:
        engine.calculate_charges(engine.molecules(phenols), METHOD, PARAMETERS, str(tmp_path))

    assert error.value.kind == "invalid_execution"
    assert str(error.value) == "Cutoff execution requires a radius."


@pytest.mark.parametrize(
    "name, content, kind, message",
    [
        ("abc_empty.sdf", "", "no_records", "No SDF molecule record found."),
        (
            "abc_element.sdf",
            "x\n  t\n\n  1  0  0  0  0  0  0  0  0  0999 V2000\n"
            "    0.0000    0.0000    0.0000 Qq  0  0\nM  END\n$$$$\n",
            "malformed",
            "Line 5, record 1 ('x'): unknown element symbol 'Qq'.",
        ),
    ],
)
def test_read_errors_have_kinds_and_do_not_name_the_stored_file(
    engine, tmp_path, name, content, kind, message
):
    path = tmp_path / name
    path.write_text(content)

    with pytest.raises(RuntimeError) as error:
        engine.molecules(str(path))

    assert error.value.kind == kind
    assert str(error.value) == message


def test_calculation_keeps_the_warnings_of_chargefw_with_their_kinds(engine, tmp_path):
    # Alanine without hydrogens.
    path = tmp_path / "abc_ala.pdb"
    path.write_text(
        "HEADER    TEST                                    01-JAN-26   1TST\n"
        "ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N\n"
        "ATOM      2  CA  ALA A   1       1.458   0.000   0.000  1.00  0.00           C\n"
        "ATOM      3  C   ALA A   1       2.009   1.420   0.000  1.00  0.00           C\n"
        "ATOM      4  O   ALA A   1       1.246   2.390   0.000  1.00  0.00           O\n"
        "ATOM      5  CB  ALA A   1       1.988  -0.773  -1.199  1.00  0.00           C\n"
        "END\n"
    )
    out = tmp_path / "charges"
    out.mkdir()

    with pytest.warns(chargefw.InputWarning):
        calculated = engine.calculate_charges(engine.molecules(str(path)), "eqeq", None, str(out))

    assert [(w.kind, w.source, w.molecule) for w in calculated.warnings] == [
        ("hydrogens_missing", "input", "1TST")
    ]
