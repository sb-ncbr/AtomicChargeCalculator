import pytest
from models.issue import IssueDto
from models.calculation import (
    CalculationConfigDto,
    CalculationDto,
    CalculationResultDto,
)

EEM = CalculationConfigDto(method="eem", parameters="EEM_example")
EQEQ = CalculationConfigDto(method="eqeq", parameters=None)
NAMES = {"hash1": "first.sdf", "hash2": "second.sdf"}


def calculation(file_hash: str, config: CalculationConfigDto, name: str | None = None):
    return CalculationDto(
        file=name or NAMES[file_hash],
        file_hash=file_hash,
        charges={f"{file_hash}-{config.method}": [0.0]},
        config=config,
    )


@pytest.mark.asyncio
async def test_unavailable_charges_name_the_method_parameters_and_file():
    from unittest.mock import AsyncMock, Mock

    from api.v1.routes.charges import _unavailable_charges
    from models.calculation import CalculationFailureDto
    from models.method import Method
    from models.parameters import Parameters

    service = Mock()
    service.get_available_methods.return_value = [
        Method(name="EEM", internal_name="eem", full_name="", publication=None, type="3D", has_parameters=True)
    ]
    service.get_available_parameters = AsyncMock(
        return_value=[Parameters(full_name="Example", internal_name="EEM_example", publication="", method="eem", notes="")]
    )
    failed = CalculationResultDto(
        config=EEM,
        calculations=[],
        failures=[
            CalculationFailureDto(
                file="first.sdf",
                file_hash="hash1",
                message="failed",
                kind="formal_charge_unsupported",
                issues=[
                    IssueDto(
                        kind="formal_charge_unsupported",
                        message="failed",
                        source="rejection",
                        molecule="ammonium",
                    )
                ],
            )
        ],
    )

    assert await _unavailable_charges([failed], service) == [
        {
            "method": "eem",
            "methodName": "EEM",
            "parameters": "EEM_example",
            "parametersName": "Example",
            "file": "first.sdf",
            "message": "failed",
            "kind": "formal_charge_unsupported",
            "issues": [
                {
                    "kind": "formal_charge_unsupported",
                    "message": "failed",
                    "source": "rejection",
                    "molecule": "ammonium",
                    "atomIndices": [],
                }
            ],
        }
    ]


def test_file_warnings_are_listed_once_per_file():
    from api.v1.routes.charges import _file_warnings

    def warned(config):
        result = calculation("hash1", config)
        result.warnings = [
            IssueDto(
                kind="unbonded_residue_atoms",
                message="2 atoms in 1 residue have no bonds",
                source="import",
                molecule="first",
                atom_indices=[5, 6],
            ),
            IssueDto(kind="hydrogens_missing", message="no hydrogen atoms", source="input"),
        ]
        return result

    results = [
        CalculationResultDto(config=EEM, calculations=[warned(EEM), calculation("hash2", EEM)]),
        CalculationResultDto(config=EQEQ, calculations=[warned(EQEQ)]),
    ]

    missing = {
        "file": "first.sdf",
        "kind": "hydrogens_missing",
        "message": "no hydrogen atoms",
        "source": "input",
        "molecule": None,
        "atomIndices": [],
    }
    # The warning about reading the file is listed once; those about a calculation name it.
    assert _file_warnings(results) == [
        {
            "file": "first.sdf",
            "kind": "unbonded_residue_atoms",
            "message": "2 atoms in 1 residue have no bonds",
            "source": "import",
            "molecule": "first",
            "atomIndices": [5, 6],
        },
        {**missing, "method": "eem", "parameters": "EEM_example"},
        {**missing, "method": "eqeq", "parameters": None},
    ]


def failing_services():
    from unittest.mock import AsyncMock, Mock

    from models.calculation import CalculationFailureDto

    service = Mock()
    service.get_available_methods.return_value = []
    service.calculate_charges = AsyncMock(
        return_value=[
            CalculationResultDto(
                config=EEM,
                calculations=[],
                failures=[
                    CalculationFailureDto(
                        file="first.sdf", file_hash="hash1", message="Boom.", kind="boom"
                    )
                ],
            )
        ]
    )
    io = Mock()
    io.get_file_size.return_value = 1
    io.max_file_size = 100
    return service, io


def test_file_warnings_of_a_failed_file_are_listed():
    from api.v1.routes.charges import _file_warnings
    from models.calculation import CalculationFailureDto

    unbonded = IssueDto(kind="unbonded_residue_atoms", message="no bonds", source="import")
    failure = CalculationFailureDto(
        file="second.sdf",
        file_hash="hash2",
        message="failed",
        kind="atom_ids_unsupported",
        warnings=[unbonded],
    )
    results = [
        CalculationResultDto(config=EEM, calculations=[calculation("hash1", EEM)], failures=[failure])
    ]

    assert [(w["file"], w["kind"]) for w in _file_warnings(results)] == [
        ("second.sdf", "unbonded_residue_atoms")
    ]


@pytest.mark.asyncio
async def test_a_request_waiting_for_charges_fails_when_no_charges_were_calculated():
    from unittest.mock import Mock

    from api.v1.exceptions import BadRequestError
    from api.v1.routes.charges import calculate_charges
    from api.v1.schemas.charges import CalculateChargesRequest
    from models.calculation import CalculationState

    request = Mock()
    request.state.user = None
    storage = Mock()
    storage.get_calculation_set.return_value = None
    service, io = failing_services()

    with pytest.raises(BadRequestError) as error:
        await calculate_charges(
            request,
            CalculateChargesRequest(
                configs=[{"method": "eem", "parameters": "EEM_example"}], file_hashes=["hash1"]
            ),
            Mock(),
            response_format="charges",
            charge_service=service,
            storage_service=storage,
            mmcif_service=Mock(),
            io_service=io,
        )

    assert error.value.status_code == 400
    assert "first.sdf: Boom." in error.value.detail
    assert io.change_computation_state.call_args.args[2] is CalculationState.FAILED


@pytest.mark.asyncio
async def test_a_background_calculation_records_its_failure():
    from unittest.mock import Mock

    from api.v1.routes.charges import _calculate_charges_in_background
    from models.calculation import CalculationState
    from models.setup import AdvancedSettingsDto

    service, io = failing_services()

    await _calculate_charges_in_background(
        "comp", ["hash1"], AdvancedSettingsDto(), [EEM], None, service, Mock(), Mock(), io
    )

    state, note = io.change_computation_state.call_args.args[2:]
    assert state is CalculationState.FAILED
    assert "first.sdf: Boom." in note
