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


def test_a_configuration_must_name_a_method():
    from api.v1.schemas.charges import CalculateChargesRequest
    from pydantic import ValidationError

    CalculateChargesRequest(configs=[], file_hashes=["hash1"])
    with pytest.raises(ValidationError, match="must name a method"):
        CalculateChargesRequest(
            configs=[{"method": "eqeq"}, {"method": None}], file_hashes=["hash1"]
        )


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


@pytest.mark.asyncio
async def test_unknown_parameters_are_rejected_before_calculating():
    from unittest.mock import Mock

    from api.v1.exceptions import BadRequestError
    from api.v1.routes.charges import calculate_charges
    from api.v1.schemas.charges import CalculateChargesRequest

    request = Mock()
    request.state.user = None
    storage = Mock()
    storage.get_calculation_set.return_value = None
    service = Mock()
    service.config_error.return_value = "Parameters 'SQEqp_x' are not available for method sqeqp."
    io = Mock()

    with pytest.raises(BadRequestError) as error:
        await calculate_charges(
            request,
            CalculateChargesRequest(
                configs=[{"method": "sqeqp", "parameters": "SQEqp_x"}], file_hashes=["hash1"]
            ),
            Mock(),
            response_format="charges",
            charge_service=service,
            storage_service=storage,
            mmcif_service=Mock(),
            io_service=io,
        )

    assert error.value.status_code == 400
    assert "'SQEqp_x' are not available" in error.value.detail
    io.prepare_inputs.assert_not_called()


def failing_services():
    from unittest.mock import AsyncMock, Mock

    from models.calculation import CalculationFailureDto

    service = Mock()
    service.config_error.return_value = None
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


@pytest.mark.asyncio
async def test_suggestions_read_the_files_with_the_selection_of_the_calculation():
    from unittest.mock import AsyncMock, Mock

    from api.v1.routes.charges import best_parameters, suitable_methods
    from api.v1.schemas.charges import BestParametersRequest, SuitableMethodsRequest
    from models.parameters import Parameters

    request = Mock()
    request.state.user = None
    service = Mock()
    service.get_suitable_methods = AsyncMock(return_value=None)
    service.get_best_parameters = AsyncMock(
        return_value=Parameters(
            full_name="EEM", internal_name="EEM_x", publication="", method="eem", notes=""
        )
    )
    service.get_available_methods.return_value = [Mock(internal_name="eem")]

    await suitable_methods(
        request,
        SuitableMethodsRequest.model_validate(
            {"fileHashes": ["hash1"], "selection": "polymers", "permissiveTypes": False}
        ),
        charge_service=service,
        io_service=Mock(),
    )
    await best_parameters(
        BestParametersRequest.model_validate(
            {"methodName": "eem", "fileHash": "hash1", "selection": "polymers-and-ligands"}
        ),
        charge_service=service,
        io_service=Mock(),
    )

    settings = service.get_suitable_methods.call_args.args[1]
    assert (settings.selection, settings.permissive_types) == ("polymers", False)
    settings = service.get_best_parameters.call_args.args[2]
    assert (settings.selection, settings.permissive_types) == ("polymers-and-ligands", True)


def test_settings_of_computations_before_chargefw_3_are_shown_but_not_calculated():
    from types import SimpleNamespace

    from pydantic import ValidationError

    from models.setup import (
        AdvancedSettingsDto,
        LegacySettingsError,
        StoredSettingsDto,
        settings_for_calculation,
    )

    stored = SimpleNamespace(selection="without-hetatm", permissive_types=True)

    assert StoredSettingsDto.model_validate(stored).selection == "without-hetatm"
    with pytest.raises(LegacySettingsError, match="left out HETATM records"):
        settings_for_calculation(stored)
    with pytest.raises(ValidationError):
        AdvancedSettingsDto(selection="without-hetatm")

    current = SimpleNamespace(selection="polymers", permissive_types=False)
    assert settings_for_calculation(current) == AdvancedSettingsDto(
        selection="polymers", permissive_types=False
    )


@pytest.mark.asyncio
async def test_a_computation_before_chargefw_3_is_not_calculated_again():
    from types import SimpleNamespace
    from unittest.mock import Mock

    from api.v1.exceptions import BadRequestError
    from api.v1.routes.charges import calculate_charges
    from api.v1.schemas.charges import CalculateChargesRequest

    request = Mock()
    request.state.user = None
    storage = Mock()
    storage.get_calculation_set.return_value = SimpleNamespace(
        advanced_settings=SimpleNamespace(selection="without-hetatm", permissive_types=True)
    )
    service, io = failing_services()

    with pytest.raises(BadRequestError) as error:
        await calculate_charges(
            request,
            CalculateChargesRequest(
                configs=[{"method": "eem", "parameters": "EEM_example"}],
                file_hashes=[],
                computation_id="comp",
            ),
            Mock(),
            response_format="charges",
            charge_service=service,
            storage_service=storage,
            mmcif_service=Mock(),
            io_service=io,
        )

    assert error.value.status_code == 400
    assert "left out HETATM records" in error.value.detail
    service.calculate_charges.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("rejection", ["too_large", "no_suitable_method"])
async def test_files_of_a_rejected_request_do_not_become_inputs(rejection):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, Mock

    from api.v1.exceptions import BadRequestError
    from api.v1.routes.charges import calculate_charges
    from api.v1.schemas.charges import CalculateChargesRequest
    from integrations.chargefw.base import ChargeCalculationError

    request = Mock()
    request.state.user = None
    storage = Mock()
    storage.get_calculation_set.return_value = SimpleNamespace(
        advanced_settings=SimpleNamespace(selection="all", permissive_types=True)
    )
    service = Mock()
    service.get_computation_suitable_methods = AsyncMock(
        side_effect=ChargeCalculationError("Atom ID 'M14' is not a positive integer.", kind="x")
    )
    io = Mock()
    io.max_file_size = 100
    io.get_file_size.return_value = 1000 if rejection == "too_large" else 1

    with pytest.raises(BadRequestError) as error:
        await calculate_charges(
            request,
            CalculateChargesRequest(configs=[], file_hashes=["hash2"], computation_id="comp"),
            Mock(),
            response_format="charges",
            charge_service=service,
            storage_service=storage,
            mmcif_service=Mock(),
            io_service=io,
        )

    assert error.value.status_code == (413 if rejection == "too_large" else 400)
    io.prepare_inputs.assert_not_called()
