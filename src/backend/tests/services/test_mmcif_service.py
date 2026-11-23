from unittest.mock import Mock

import gemmi
import pytest

from app.models.calculation import (
    CalculationConfigDto,
    CalculationDto,
    CalculationResultDto,
)
from app.services.mmcif import MmCIFService

# A viewer file as a charge engine writes it: the charges name the structure's atom IDs.
VIEWER_CIF = """data_ions
loop_
_audit_conform.dict_name
_audit_conform.dict_version
_audit_conform.dict_location
mmcif_pdbx.dic 5.0 http://mmcif.pdb.org/dictionaries/ascii/mmcif_pdbx.dic
mmcif_charges_v11.dic 1.1 https://sb-ncbr.github.io/charges-schema/schemas/mmcif_charges_v11.dic
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.Cartn_x
_atom_site.Cartn_y
_atom_site.Cartn_z
14 Mg 0 0 3
15 Ca 3 0 3
loop_
_sb_ncbr_partial_atomic_charges_meta.id
_sb_ncbr_partial_atomic_charges_meta.type
_sb_ncbr_partial_atomic_charges_meta.method
_sb_ncbr_partial_atomic_charges_meta.parameter_set
1 empirical eem EEM_example
loop_
_sb_ncbr_partial_atomic_charges.type_id
_sb_ncbr_partial_atomic_charges.atom_id
_sb_ncbr_partial_atomic_charges.charge
1 14 1.5
1 15 1.6
"""


@pytest.fixture
def service(tmp_path):
    io = Mock()
    io.get_charges_path.return_value = str(tmp_path)
    (tmp_path / "ions.fw2.cif").write_text(VIEWER_CIF)
    return MmCIFService(logger=Mock(), io=io)


def result(method: str, parameters: str | None, charges: list[float]) -> CalculationResultDto:
    config = CalculationConfigDto(method=method, parameters=parameters)
    return CalculationResultDto(
        config=config,
        calculations=[
            CalculationDto(
                file="ions.cif", file_hash="hash", charges={"ions": charges}, config=config
            )
        ],
    )


def test_charge_sets_use_the_atom_ids_of_the_file(service, tmp_path):
    service.write_to_mmcif(
        None, "comp", [result("eem", "EEM_example", [1.5, 1.6]), result("eqeq", None, [1.0, 2.0])]
    )

    block = gemmi.cif.read(str(tmp_path / "ions.fw2.cif")).sole_block()
    assert [list(row) for row in block.find("_sb_ncbr_partial_atomic_charges_meta.", ["id", "method"])] == [
        ["1", "'eem/EEM_example'"],
        ["2", "'eqeq/None'"],
    ]
    assert [
        list(row)
        for row in block.find("_sb_ncbr_partial_atomic_charges.", ["type_id", "atom_id", "charge"])
    ] == [
        ["1", "14", "1.5000"],
        ["1", "15", "1.6000"],
        ["2", "14", "1.0000"],
        ["2", "15", "2.0000"],
    ]
    # The rows follow version 1.0 of the charges dictionary.
    assert list(block.find_values("_audit_conform.dict_name")) == [
        "mmcif_pdbx.dic",
        "mmcif_charges_v10.dic",
    ]


def test_charge_count_must_match_the_charged_atoms(service):
    with pytest.raises(ValueError, match="2 charged atoms"):
        service.write_to_mmcif(None, "comp", [result("eqeq", None, [1.0, 2.0, 3.0])])


def test_molecule_lists_only_the_charge_sets_it_has(service, tmp_path):
    failed = result("gdac", "GDAC_original", [])
    failed.calculations = []

    service.write_to_mmcif(
        None, "comp", [failed, result("eqeq", None, [1.0, 2.0])]
    )

    block = gemmi.cif.read(str(tmp_path / "ions.fw2.cif")).sole_block()
    assert [list(row) for row in block.find("_sb_ncbr_partial_atomic_charges_meta.", ["id", "method"])] == [
        ["1", "'eqeq/None'"],
    ]
    assert [row[0] for row in block.find("_sb_ncbr_partial_atomic_charges.", ["type_id"])] == ["1", "1"]


def test_charges_dictionary_is_declared_whatever_the_case_of_the_tags(service, tmp_path):
    path = tmp_path / "ions.fw2.cif"
    text = VIEWER_CIF
    for tag in ("dict_name", "dict_version", "dict_location"):
        text = text.replace(f"_audit_conform.{tag}", f"_audit_conform.{tag.upper()}")
    path.write_text(text)

    service.write_to_mmcif(None, "comp", [result("eqeq", None, [1.0, 2.0])])

    text = path.read_text()
    block = gemmi.cif.read_string(text).sole_block()
    assert list(block.find_values("_audit_conform.dict_name")) == [
        "mmcif_pdbx.dic",
        "mmcif_charges_v10.dic",
    ]
    assert "_audit_conform.DICT_NAME" in text
