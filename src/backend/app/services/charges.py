"""Charge calculation service."""

import asyncio
import os
import traceback

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from models.calculation import (
    CalculationDto,
    CalculationConfigDto,
    CalculationFailureDto,
    CalculationResultDto,
)
from models.issue import IssueDto
from models.molecule_info import MoleculeSetStats
from models.method import Method
from models.parameters import Parameters
from models.setup import AdvancedSettingsDto, Selection, settings_for_calculation
from models.suitable_methods import SuitableMethods

from integrations.chargefw.base import UNEXPECTED_ERROR, ChargeEngine, EngineError, Molecules

from api.v1.constants import CHARGES_OUTPUT_EXTENSION

from services.io import IOService
from services.logging.base import LoggerBase
from services.mmcif import MmCIFService
from services.calculation_storage import CalculationStorageService


class ChargeService:
    """Reads files, suggests methods, and calculates charges with the charge engine."""

    def __init__(
        self,
        engine: ChargeEngine,
        logger: LoggerBase,
        io: IOService,
        mmcif_service: MmCIFService,
        calculation_storage: CalculationStorageService,
        max_workers: int = 4,
        max_concurrent_calculations: int = 4,
    ):
        self.engine = engine
        self.logger = logger
        self.io = io
        self.mmcif_service = mmcif_service
        self.calculation_storage = calculation_storage
        self.executor = ThreadPoolExecutor(max_workers)
        self.semaphore = asyncio.Semaphore(max_concurrent_calculations)

    async def _run_in_executor(self, func, *args, executor=None):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor if executor is None else executor, func, *args
        )

    # Method related operations
    def config_error(self, config: CalculationConfigDto) -> str | None:
        """Why a requested method and parameter set cannot be calculated, or None."""

        return self.engine.config_error(config.method, config.parameters)

    def get_available_methods(self) -> list[Method]:
        """Get available methods for charge calculation."""

        try:
            self.logger.info("Getting available methods.")
            methods = self.engine.get_available_methods()

            return methods
        except Exception as e:
            self.logger.error(f"Error getting available methods: {e}")
            raise e

    async def get_suitable_methods(
        self,
        file_hashes: list[str],
        settings: AdvancedSettingsDto | None = None,
        user_id: str | None = None,
    ) -> SuitableMethods:
        """Get methods suitable for the files, read as a calculation with the settings reads them."""

        try:
            self.logger.info(
                f"Getting suitable methods for file hashes '{file_hashes}'"
            )

            return await self._find_suitable_methods(
                file_hashes, settings or AdvancedSettingsDto(), user_id
            )
        except Exception as e:
            self.logger.error(
                f"Error getting suitable methods for file hashes '{file_hashes}': {e}"
            )
            raise e

    async def get_computation_suitable_methods(
        self,
        computation_id: str,
        user_id: str | None,
        settings: AdvancedSettingsDto | None = None,
        file_hashes: list[str] | None = None,
    ) -> SuitableMethods:
        """Get methods suitable for the files of a computation, read as the computation reads them.

        Args:
            file_hashes: The files to be calculated; all inputs of the computation if None.
        """

        try:
            self.logger.info(
                f"Getting suitable methods for computation '{computation_id}'"
            )

            calculation_set = self.calculation_storage.get_calculation_set(
                computation_id
            )

            if calculation_set is not None:
                settings = settings_for_calculation(calculation_set.advanced_settings)

            if settings is None:
                settings = AdvancedSettingsDto()

            if file_hashes is None:
                workdir = self.io.get_inputs_path(computation_id, user_id)
                file_hashes = [
                    self.io.parse_filename(file)[0] for file in self.io.listdir(workdir)
                ]

            return await self._find_suitable_methods(file_hashes, settings, user_id)
        except Exception as e:
            self.logger.error(
                f"Error getting suitable methods for computation '{computation_id}': {e}"
            )
            raise e

    async def _find_suitable_methods(
        self, file_hashes: list[str], settings: AdvancedSettingsDto, user_id: str | None
    ) -> SuitableMethods:
        """Helper method to find suitable methods for calculation."""

        suitable_methods = Counter()
        workdir = self.io.get_file_storage_path(user_id)

        dir_contents = self.io.listdir(workdir)
        for file_hash in file_hashes:
            file = next(
                (f for f in dir_contents if self.io.parse_filename(f)[0] == file_hash),
                None,
            )
            if file is None:
                self.logger.warn(
                    f"File with hash {file_hash} not found in {workdir}, skipping."
                )
                continue

            input_file = os.path.join(workdir, file)
            molecules = await self.read_molecules(
                input_file,
                settings.selection,
                settings.permissive_types,
            )
            methods: list[
                tuple[Method, list[Parameters]]
            ] = await self._run_in_executor(
                self.engine.get_suitable_methods, molecules
            )
            for method, parameters in methods:
                if not parameters or len(parameters) == 0:
                    suitable_methods[(method,)] += 1
                else:
                    for p in parameters:
                        suitable_methods[(method, p)] += 1

        all_valid = [
            pair
            for pair in suitable_methods
            if suitable_methods[pair] == len(file_hashes)
        ]

        # Remove duplicates from methods
        tmp = {}
        for data in all_valid:
            tmp[data[0]] = None

        methods = list(tmp.keys())

        parameters = defaultdict(list)
        for pair in all_valid:
            if len(pair) == 2:
                parameters[pair[0]].append(pair[1])

        parameters_with_metadata = {
            method.internal_name: params for method, params in parameters.items()
        }
        return SuitableMethods(methods=methods, parameters=parameters_with_metadata)

    async def get_available_parameters(self, method: str) -> list[Parameters]:
        """Get available parameters for charge calculation method."""

        try:
            self.logger.info(f"Getting available parameters for method {method}.")
            parameters = await self._run_in_executor(
                self.engine.get_available_parameters, method
            )

            return parameters
        except Exception as e:
            self.logger.error(
                f"Error getting available parameters for method {method}: {e}"
            )
            raise e

    async def get_best_parameters(
        self, method: str, file_path: str, settings: AdvancedSettingsDto | None = None
    ) -> Parameters | None:
        """Get best parameters of the method for the file, read as a calculation with the
        settings reads it."""

        settings = settings or AdvancedSettingsDto()
        try:
            molecules = await self.read_molecules(
                file_path, settings.selection, settings.permissive_types
            )

            self.logger.info(f"Getting best parameters for method {method}.")
            parameters = await self._run_in_executor(
                self.engine.get_best_parameters,
                molecules,
                method,
            )

            return parameters
        except Exception as e:
            self.logger.error(f"Error getting best parameters for method {method}: {e}")
            raise e

    async def read_molecules(
        self,
        file_path: str,
        selection: Selection = "all",
        permissive_types: bool = False,
    ) -> Molecules:
        """Load molecules from a file"""
        try:
            self.logger.info(f"Loading molecules from file {file_path}.")
            molecules = await self._run_in_executor(
                self.engine.molecules,
                file_path,
                selection,
                permissive_types,
            )

            return molecules
        except Exception as e:
            self.logger.error(f"Error loading molecules from file {file_path}: {e}")
            raise e

    async def calculate_charges(
        self,
        computation_id: str,
        settings: AdvancedSettingsDto,
        data: dict[CalculationConfigDto, list[str]],
        user_id: str | None,
    ) -> list[CalculationResultDto]:
        """Calculate charges for provided files.

        Args:
            computation_id (str): Computation id.
            settings (AdvancedSettingsDto): Settings the files are read with.
            data (dict[CalculationConfigDto, list[str]]): File hashes to calculate for each
                configuration.
            user_id (str): User id making the calculation.

        Returns:
            list[CalculationResultDto]: One result per configuration, in the order of
                `data`. Each lists its files in their order there: those with charges
                under `calculations`, the failed ones under `failures`.
        """

        calculations = await asyncio.gather(
            *[
                self._calculate_charges(
                    user_id, computation_id, settings, config, file_hashes
                )
                for config, file_hashes in data.items()
            ],
            return_exceptions=False,
        )

        return calculations

    async def _calculate_charges(
        self,
        user_id: str | None,
        computation_id: str,
        settings: AdvancedSettingsDto,
        config: CalculationConfigDto,
        file_hashes: list[str],
    ) -> CalculationResultDto:
        """Calculate charges for provided files."""

        self.logger.info(
            f"Calculating charges with method {config.method} and parameters {config.parameters}."
        )

        workdir = self.io.get_file_storage_path(user_id)

        async def process_file(
            file_hash: str, config: CalculationConfigDto
        ) -> CalculationDto | CalculationFailureDto | None:
            file_name = next(
                (
                    file
                    for file in self.io.listdir(workdir)
                    if self.io.parse_filename(file)[0] == file_hash
                ),
                None,
            )

            if file_name is None:
                self.logger.warn(
                    f"File with hash {file_hash} not found in {workdir}, skipping."
                )
                return

            async with self.semaphore:
                charges_dir = self.io.get_charges_path(computation_id, user_id)
                self.io.create_dir(charges_dir)

                full_path = os.path.join(workdir, file_name)
                file_name = self.io.parse_filename(file_name)[1]

                # Each method and parameter set is a calculation of its own: when it fails,
                # its charges are not available and the other configurations go on.
                warnings: list[IssueDto] = []
                try:
                    molecules = await self.read_molecules(
                        full_path,
                        settings.selection,
                        settings.permissive_types,
                    )

                    warnings = await self._run_in_executor(self.engine.warnings, molecules)
                    calculated = await self._run_in_executor(
                        self.engine.calculate_charges,
                        molecules,
                        config.method,
                        config.parameters,
                        charges_dir,
                    )
                except EngineError as e:
                    # The engine explains the failure: a message for users, the kind of
                    # the reason, and every issue it found.
                    self.logger.warn(
                        f"Charges of {file_name} with {config.method} ({config.parameters}) "
                        f"are not available ({e.kind}): {e}"
                    )
                    return CalculationFailureDto(
                        file=file_name,
                        file_hash=file_hash,
                        message=str(e),
                        kind=e.kind,
                        issues=e.issues,
                        warnings=warnings,
                    )
                except Exception:  # noqa: BLE001 - one failed pair must not stop the others; logged below
                    self.logger.error(
                        f"Error calculating charges of {file_name} with {config.method} "
                        f"({config.parameters}): {traceback.format_exc()}"
                    )
                    return CalculationFailureDto(
                        file=file_name,
                        file_hash=file_hash,
                        message="An unexpected error occurred.",
                        kind=UNEXPECTED_ERROR,
                        warnings=warnings,
                    )

                return CalculationDto(
                    file=file_name,
                    file_hash=file_hash,
                    charges=calculated.charges,
                    config=config,
                    warnings=[*warnings, *calculated.warnings],
                )

        try:
            outcomes = [
                outcome
                for outcome in await asyncio.gather(
                    *[process_file(file_hash, config) for file_hash in file_hashes],
                    return_exceptions=False,
                )
                if outcome is not None
            ]
            config_dto = CalculationConfigDto(
                method=config.method,
                parameters=config.parameters,
            )

            return CalculationResultDto(
                config=config_dto,
                calculations=[o for o in outcomes if isinstance(o, CalculationDto)],
                failures=[o for o in outcomes if isinstance(o, CalculationFailureDto)],
            )
        except Exception as e:
            self.logger.error(f"Error calculating charges: {traceback.format_exc()}")
            raise e

    async def info(self, path: str) -> MoleculeSetStats:
        """Get information about the provided file."""

        try:
            self.logger.info(f"Getting info for file {path}.")

            molecules = await self.read_molecules(path)
            info = await self._run_in_executor(self.engine.info, molecules)

            return MoleculeSetStats(info)
        except Exception as e:
            self.logger.error(
                f"Error getting info for file {path}: {traceback.format_exc()}"
            )
            raise e

    def get_calculation_molecules(self, path: str) -> list[str]:
        """Returns molecules stored in the provided path.

        Args:
            path (str): Path to computation results.

        Raises:
            FileNotFoundError: If the provided path does not exist.

        Returns:
            list[str]: List of molecule names.
        """
        if not self.io.path_exists(path):
            raise FileNotFoundError()

        molecule_files = [
            file
            for file in self.io.listdir(path)
            if file.endswith(CHARGES_OUTPUT_EXTENSION)
        ]
        molecules = [
            file.replace(CHARGES_OUTPUT_EXTENSION, "") for file in molecule_files
        ]

        return molecules

    def delete_calculation(self, computation_id: str, user_id: str) -> None:
        """Delete the provided computation (from database and filesystem).

        Args:
            computation_id (str): Computation id.
            user_id (str): User id.

        Raises:
            e: Error deleting computation.
        """
        try:
            self.calculation_storage.delete_calculation_set(computation_id)
            self.io.delete_computation(computation_id, user_id)
        except Exception as e:
            self.logger.error(
                f"Error deleting computation {computation_id}: {traceback.format_exc()}"
            )
            raise e
