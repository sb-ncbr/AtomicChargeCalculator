from pathlib import Path

import chargefw
import pytest

from integrations.chargefw.base import MoleculeReadError
from app.integrations.chargefw.chargefw import ChargeFWLocal

PHENOLS = str(Path(__file__).parent.parent / "data" / "integrations" / "phenols.sdf")

# Water, a magnesium ion, and a calcium ion; no polymer.
IONS_CIF = """data_ions
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
HETATM 1 O O . HOH W . 0 0 0 0 5 W 1 1
HETATM 2 H H1 . HOH W . 0.96 0 0 0 5 W 1 1
HETATM 3 H H2 . HOH W . -0.24 0.93 0 0 5 W 1 1
HETATM 4 Mg MG . MG I . 0 0 3 0 9 I 2 1
HETATM 5 Ca CA . CA I . 3 0 3 0 10 I 3 1
"""


@pytest.fixture(scope="module")
def engine():
    return ChargeFWLocal()


@pytest.fixture
def ions_cif(tmp_path):
    path = tmp_path / "hash_ions.cif"
    path.write_text(IONS_CIF)
    return str(path)


def test_info_counts_molecules_atoms_and_elements(engine):
    info = engine.info(engine.molecules(PHENOLS))

    assert info["total_molecules"] == 7
    assert info["total_atoms"] == 121
    assert {c["symbol"]: c["count"] for c in info["atom_type_counts"]} == {
        "C": 50,
        "H": 53,
        "O": 13,
        "N": 3,
        "Cl": 2,
    }


def test_suitable_methods_list_each_parameter_set_once_in_order(engine):
    suitable = engine.get_suitable_methods(engine.molecules(PHENOLS))

    method, parameters = suitable[0]
    assert method.internal_name == "sqeqp"
    assert parameters[0].internal_name == "SQEqp_Schindler2021_CCD_gen"

    names = [m.internal_name for m, _ in suitable]
    assert len(names) == len(set(names))
    for _, parameters in suitable:
        ids = [p.internal_name for p in parameters]
        assert len(ids) == len(set(ids))


def test_best_parameters(engine):
    molecules = engine.molecules(PHENOLS)

    assert engine.get_best_parameters(molecules, "sqeqp").internal_name == (
        "SQEqp_Schindler2021_CCD_gen"
    )
    assert engine.get_best_parameters(molecules, "eqeq") is None


def test_selection_chooses_atoms_of_structures(engine, ions_cif):
    def atom_count(selection):
        molecules = engine.molecules(ions_cif, selection)
        return sum(molecule.atom_count for molecule in molecules.collection)

    assert atom_count("all") == 5
    assert atom_count("polymers-and-ligands") == 2

    with pytest.raises(RuntimeError, match="no selected atoms"):
        atom_count("polymers")


# Alanine and selenomethionine, a modified residue written as HETATM records.
PDB_WITH_MODIFIED_RESIDUE = """HEADER    TEST                                    01-JAN-26   1TST
ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       1.458   0.000   0.000  1.00  0.00           C
ATOM      3  C   ALA A   1       2.009   1.420   0.000  1.00  0.00           C
ATOM      4  O   ALA A   1       1.246   2.390   0.000  1.00  0.00           O
ATOM      5  CB  ALA A   1       1.988  -0.773  -1.199  1.00  0.00           C
HETATM    6  N   MSE A   2       3.332   1.536   0.000  1.00  0.00           N
HETATM    7  CA  MSE A   2       3.970   2.846   0.000  1.00  0.00           C
END
"""


# Alanine and a new ligand: the file has no CONECT records for it and the component dictionary
# has no entry, as the wwPDB keeps the codes 01 to 99 for new ligands.
PDB_WITH_NEW_LIGAND = """HEADER    TEST                                    01-JAN-26   1TST
ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       1.458   0.000   0.000  1.00  0.00           C
ATOM      3  C   ALA A   1       2.009   1.420   0.000  1.00  0.00           C
ATOM      4  O   ALA A   1       1.246   2.390   0.000  1.00  0.00           O
ATOM      5  CB  ALA A   1       1.988  -0.773  -1.199  1.00  0.00           C
HETATM    6  C1   01 A 101       8.000   0.000   0.000  1.00  0.00           C
HETATM    7  O1   01 A 101       9.400   0.000   0.000  1.00  0.00           O
END
"""


def test_polymers_keep_their_modified_residues(engine, tmp_path):
    path = tmp_path / "hash_mse.pdb"
    path.write_text(PDB_WITH_MODIFIED_RESIDUE)

    molecules = engine.molecules(str(path), "polymers")

    assert sum(molecule.atom_count for molecule in molecules.collection) == 7


def test_bonds_the_file_lacks_come_from_the_component_dictionary(engine, tmp_path):
    path = tmp_path / "hash_mse.pdb"
    path.write_text(PDB_WITH_MODIFIED_RESIDUE)

    # The file has no CONECT records for MSE; its bond N-CA is in the dictionary.
    molecules = engine.molecules(str(path))

    assert engine.warnings(molecules) == []
    assert [5, 6, 1] in molecules.collection[0].bonds.tolist()


def test_settings_of_former_versions_are_refused():
    from pydantic import ValidationError

    from app.models.setup import AdvancedSettingsDto

    with pytest.raises(ValidationError, match="readHetatm"):
        AdvancedSettingsDto.model_validate({"readHetatm": False})
    with pytest.raises(ValidationError, match="selection"):
        AdvancedSettingsDto.model_validate({"selection": "ligands"})


def test_permissive_types_sets_parameter_matching(engine):
    assert engine.molecules(PHENOLS, permissive_types=True).parameter_matching == "permissive"
    assert engine.molecules(PHENOLS, permissive_types=False).parameter_matching == "strict"


def test_unreadable_file_is_a_runtime_error(engine, tmp_path):
    broken = tmp_path / "hash_broken.sdf"
    broken.write_text("not a molecule\n")

    with pytest.raises(RuntimeError):
        engine.molecules(str(broken))

    with pytest.raises(ValueError, match="Unsupported file type"):
        engine.molecules(str(tmp_path / "hash_file.xyz"))


def test_atoms_without_bonds_are_reported(engine, tmp_path):
    path = tmp_path / "hash_ligand.pdb"
    path.write_text(PDB_WITH_NEW_LIGAND)

    with pytest.warns(chargefw.InputWarning, match="unbonded_residue_atoms"):
        molecules = engine.molecules(str(path))

    warning, rejected = engine.warnings(molecules)
    assert rejected.kind == "component_entries_rejected"
    assert "a temporary ligand name" in rejected.message
    assert (warning.kind, warning.source, warning.molecule) == (
        "unbonded_residue_atoms",
        "import",
        "1TST",
    )
    assert "have no bonds" in warning.message
    assert "01 A 101" in warning.message
    # The two atoms of the ligand, by their positions in the molecule.
    assert warning.atom_indices == [5, 6]

    assert engine.warnings(engine.molecules(PHENOLS)) == []


def test_running_out_of_memory_while_reading_says_the_structure_is_too_large(
    engine, monkeypatch
):
    def out_of_memory(*args, **kwargs):
        raise MemoryError

    monkeypatch.setattr(chargefw.io, "read", out_of_memory)
    with pytest.raises(MoleculeReadError, match="too large") as error:
        engine.molecules(PHENOLS)
    assert error.value.kind == "out_of_memory"
