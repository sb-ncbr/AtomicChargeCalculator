from typing import Literal
from unittest.mock import AsyncMock, Mock
import pytest

from app.models.method import Method
from app.models.parameters import Parameters
from app.models.calculation import (
    CalculationConfigDto,
    CalculationDto,
    CalculationResultDto,
)
from app.models.setup import AdvancedSettingsDto
from app.models.suitable_methods import SuitableMethods
from app.services.charges import ChargeService


@pytest.fixture
def engine_mock():
    engine = Mock()
    engine.warnings.return_value = []
    return engine


@pytest.fixture
def logger_mock():
    return Mock()


@pytest.fixture
def io_mock():
    mock = Mock()
    mock.parse_filename = Mock(side_effect=lambda f: (f.split("_")[0], f.split("_")[1]))
    mock.listdir = Mock(return_value=["hash1_file1.pdb", "hash2_file2.pdb"])
    mock.get_file_storage_path = Mock(return_value="/storage")
    mock.get_inputs_path = Mock(return_value="/inputs")
    mock.get_charges_path = Mock(return_value="/charges")
    mock.create_dir = Mock()
    mock.store_configs = AsyncMock()
    mock.path_exists = Mock(return_value=True)
    return mock


@pytest.fixture
def mmcif_service_mock():
    return Mock()


@pytest.fixture
def calculation_storage_mock():
    mock = Mock()
    mock.get_calculation_set = Mock(return_value=None)
    return mock


@pytest.fixture
def service(engine_mock, logger_mock, io_mock, mmcif_service_mock, calculation_storage_mock):
    return ChargeService(
        engine=engine_mock,
        logger=logger_mock,
        io=io_mock,
        mmcif_service=mmcif_service_mock,
        calculation_storage=calculation_storage_mock,
        max_workers=2,
        max_concurrent_calculations=2,
    )


def get_method(
    internal_name: str,
    name: str = "",
    fullName: str = "",
    publication: str = "",
    type: Literal["2D", "3D", "other"] = "3D",
    has_parameters: bool = False,
) -> Method:
    return Method(
        internal_name=internal_name,
        name=name,
        full_name=fullName,
        publication=publication,
        type=type,
        has_parameters=has_parameters,
    )


def get_parameters(
    internal_name: str, full_name: str = "", method: str = "", publication: str = "", notes: str = ""
) -> Parameters:
    return Parameters(
        internal_name=internal_name, full_name=full_name, method=method, publication=publication, notes=notes
    )


class TestChargeService:
    def test_get_available_methods(self, service, engine_mock):
        """Test getting available methods."""

        expected_methods = [get_method("method1"), get_method("method2")]
        engine_mock.get_available_methods.return_value = expected_methods

        result = service.get_available_methods()

        assert result == expected_methods
        engine_mock.get_available_methods.assert_called_once()
        service.logger.info.assert_called_once_with("Getting available methods.")

    def test_get_available_methods_error(self, service, engine_mock):
        """Test handling exceptions when creating a directory."""

        engine_mock.get_available_methods.side_effect = Exception("Test error")

        with pytest.raises(Exception, match="Test error"):
            service.get_available_methods()

        service.logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_available_parameters(self, service, engine_mock):
        """Test getting available parameters."""

        method = "method1"
        expected_params = [get_parameters("param1"), get_parameters("param2")]
        engine_mock.get_available_parameters.return_value = expected_params

        result = await service.get_available_parameters(method)

        assert result == expected_params
        engine_mock.get_available_parameters.assert_called_once_with(method)
        service.logger.info.assert_called_once_with(
            f"Getting available parameters for method {method}."
        )

    @pytest.mark.asyncio
    async def test_get_best_parameters(self, service, engine_mock):
        """Test getting best parameters."""

        method = "method1"
        file_path = "/path/to/file.pdb"
        expected_params = get_parameters("best_params")

        molecules_mock = Mock()
        service.read_molecules = AsyncMock(return_value=molecules_mock)
        engine_mock.get_best_parameters.return_value = expected_params

        result = await service.get_best_parameters(method, file_path)

        assert result == expected_params
        service.read_molecules.assert_called_once_with(file_path, permissive_types=True)
        engine_mock.get_best_parameters.assert_called_once_with(molecules_mock, method)

    @pytest.mark.asyncio
    async def test_read_molecules(self, service, engine_mock):
        """Test reading molecules."""

        file_path = "/path/to/file.pdb"
        molecules_mock = Mock()
        engine_mock.molecules.return_value = molecules_mock

        result = await service.read_molecules(file_path, True, False, True)

        assert result == molecules_mock
        engine_mock.molecules.assert_called_once_with(file_path, True, False, True)
        service.logger.info.assert_called_once_with(f"Loading molecules from file {file_path}.")

    @pytest.mark.asyncio
    async def test_get_suitable_methods(self, service):
        """Test getting suitable methods."""

        file_hashes = ["hash1", "hash2"]

        # _find_suitable_methods mocks
        mock_suitable_methods = SuitableMethods(
            methods=[get_method("method1")], parameters={"method1": [get_parameters("param1")]}
        )
        service._find_suitable_methods = AsyncMock(return_value=mock_suitable_methods)

        result = await service.get_suitable_methods(file_hashes, True, "user123")

        assert result == mock_suitable_methods
        hashes, settings, user_id = service._find_suitable_methods.call_args.args
        assert (hashes, user_id) == (file_hashes, "user123")
        assert settings.model_dump() == {
            "read_hetatm": True,
            "ignore_water": False,
            "permissive_types": True,
        }
        service.logger.info.assert_called_once_with(
            f"Getting suitable methods for file hashes '{file_hashes}'"
        )

    @pytest.mark.asyncio
    async def test_get_computation_suitable_methods(self, service, calculation_storage_mock):
        """Test getting suitable methods for a computation."""

        computation_id = "comp123"
        user_id = "user123"

        advanced_settings = AdvancedSettingsDto(permissive_types=True)
        mock_calculation_set = Mock()
        mock_calculation_set.advanced_settings = advanced_settings
        calculation_storage_mock.get_calculation_set.return_value = mock_calculation_set

        # _find_suitable_methods mocks
        mock_suitable_methods = SuitableMethods(
            methods=[get_method("method1")], parameters={"method1": [get_parameters("param1")]}
        )
        service._find_suitable_methods = AsyncMock(return_value=mock_suitable_methods)

        result = await service.get_computation_suitable_methods(computation_id, user_id, advanced_settings)

        assert result == mock_suitable_methods
        calculation_storage_mock.get_calculation_set.assert_called_once_with(computation_id)
        service._find_suitable_methods.assert_called_once()
        service.logger.info.assert_called_once_with(
            f"Getting suitable methods for computation '{computation_id}'"
        )

    @pytest.mark.asyncio
    async def test_computation_suitable_methods_assess_requested_files_as_calculated(
        self, service, calculation_storage_mock
    ):
        """Suggestions read only the requested files, with the computation's settings."""

        settings = AdvancedSettingsDto(read_hetatm=False, ignore_water=True, permissive_types=False)
        calculation_storage_mock.get_calculation_set.return_value = None
        service._find_suitable_methods = AsyncMock()

        await service.get_computation_suitable_methods("comp123", "user123", settings, ["hash2"])

        service._find_suitable_methods.assert_called_once_with(["hash2"], settings, "user123")
        service.io.listdir.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_suitable_methods(self, service):
        """Test finding suitable methods."""

        file_hashes = ["hash1", "hash2"]
        permissive_types = True
        user_id = "user123"

        molecules_mock = Mock()
        service.read_molecules = AsyncMock(return_value=molecules_mock)

        method1 = get_method("method1")
        method2 = get_method("method2")
        param1 = get_parameters("param1")
        param2 = get_parameters("param2")

        service._run_in_executor = AsyncMock(
            side_effect=[
                [(method1, [param1]), (method2, [param2])],  # For first file
                [(method1, [param1])],  # For second file
            ]
        )

        settings = AdvancedSettingsDto(
            read_hetatm=False, ignore_water=True, permissive_types=permissive_types
        )
        result = await service._find_suitable_methods(file_hashes, settings, user_id)

        assert len(result.methods) == 1
        assert [call.args[1:] for call in service.read_molecules.call_args_list] == [
            (False, True, permissive_types)
        ] * len(file_hashes)
        assert method1 in result.methods
        assert len(result.parameters["method1"]) == 1
        assert result.parameters["method1"][0] == param1

    @pytest.mark.asyncio
    async def test_calculate_charges(self, service):
        """Test calculating charges."""

        computation_id = "comp123"
        user_id = "user123"
        settings = AdvancedSettingsDto()

        config = CalculationConfigDto(method="method1", parameters="param1")
        file_hashes = ["hash1", "hash2"]
        data = {config: file_hashes}

        result_dto = CalculationResultDto(
            config=config,
            calculations=[
                CalculationDto(file="file1.pdb", file_hash="hash1", charges={}, config=config),
                CalculationDto(file="file2.pdb", file_hash="hash2", charges={}, config=config),
            ],
        )

        service._calculate_charges = AsyncMock(return_value=result_dto)

        result = await service.calculate_charges(computation_id, settings, data, user_id)

        assert result == [result_dto]
        service._calculate_charges.assert_called_once_with(
            user_id, computation_id, settings, config, file_hashes
        )
        # The route writes configs.json once new and stored results are merged.
        service.io.store_configs.assert_not_called()

    @pytest.mark.asyncio
    async def test_info(self, service, engine_mock):
        """Test getting info."""

        file_path = "/path/to/file.pdb"
        molecules_mock = Mock()
        engine_mock.info.return_value = {
            "total_atoms": 0,
            "atom_type_counts": [],
            "total_molecules": 0,
        }

        service.read_molecules = AsyncMock(return_value=molecules_mock)

        result = await service.info(file_path)

        assert result.model_dump() == {
            "total_atoms": 0,
            "atom_type_counts": [],
            "total_molecules": 0,
        }
        service.read_molecules.assert_called_once_with(file_path)
        engine_mock.info.assert_called_once_with(molecules_mock)
        service.logger.info.assert_called_once_with(f"Getting info for file {file_path}.")

    def test_get_calculation_molecules(self, service, io_mock):
        """Test getting calculation molecules."""

        path = "/path/to/results"
        io_mock.listdir.return_value = ["mol1.fw2.cif", "mol2.fw2.cif", "config.json"]

        result = service.get_calculation_molecules(path)

        assert result == ["mol1", "mol2"]
        io_mock.path_exists.assert_called_once_with(path)
        io_mock.listdir.assert_called_once_with(path)

    def test_get_calculation_molecules_not_found(self, service, io_mock):
        """Test getting calculation molecules from a nonexistent path."""

        path = "/path/to/nonexistent"
        io_mock.path_exists.return_value = False
        with pytest.raises(FileNotFoundError):
            service.get_calculation_molecules(path)

    def test_delete_calculation(self, service):
        """Test deleting a calculation."""

        computation_id = "comp123"
        user_id = "user123"

        service.delete_calculation(computation_id, user_id)

        service.calculation_storage.delete_calculation_set.assert_called_once_with(computation_id)
        service.io.delete_computation.assert_called_once_with(computation_id, user_id)

    def test_delete_calculation_error(self, service, calculation_storage_mock):
        """Test handling exceptions when deleting a calculation."""

        computation_id = "comp123"
        user_id = "user123"
        calculation_storage_mock.delete_calculation_set.side_effect = Exception("Test error")
        with pytest.raises(Exception):
            service.delete_calculation(computation_id, user_id)

        service.logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_a_failed_configuration_does_not_stop_the_others(service, engine_mock):
    # The same modules as the service imports, so that it recognizes the error.
    from integrations.chargefw.base import CalculatedCharges, ChargeCalculationError
    from models.issue import IssueDto

    good = CalculationConfigDto(method="eqeq", parameters=None)
    bad = CalculationConfigDto(method="gdac", parameters="GDAC_original")
    service.read_molecules = AsyncMock(return_value=Mock())

    def calculate(molecules, method, parameters, out_dir):
        if method == "gdac":
            raise ChargeCalculationError(
                "mmCIF charge is outside the dictionary range [-10, 10].", kind="unrepresentable"
            )
        return CalculatedCharges(charges={"mol": [0.0]}, warnings=[charge_warning])

    import_warning = IssueDto(kind="unbonded_residue_atoms", message="no bonds", source="import")
    charge_warning = IssueDto(kind="charge_out_of_range", message="far", source="charge")
    engine_mock.warnings.return_value = [import_warning]

    engine_mock.calculate_charges.side_effect = calculate

    results = await service.calculate_charges(
        "comp", AdvancedSettingsDto(), {good: ["hash1"], bad: ["hash1"]}, None
    )

    by_method = {r.config.method: r for r in results}
    assert [c.charges for c in by_method["eqeq"].calculations] == [{"mol": [0.0]}]
    assert by_method["gdac"].calculations == []
    # The warnings of reading the file and of the calculation are kept with their kinds.
    assert [w.kind for c in by_method["eqeq"].calculations for w in c.warnings] == [
        "unbonded_residue_atoms",
        "charge_out_of_range",
    ]
    assert [(f.file, f.message, f.kind) for f in by_method["gdac"].failures] == [
        ("file1.pdb", "mmCIF charge is outside the dictionary range [-10, 10].", "unrepresentable")
    ]
    # The failed calculation keeps what the engine warns about in the file.
    assert [w.kind for f in by_method["gdac"].failures for w in f.warnings] == [
        "unbonded_residue_atoms"
    ]
