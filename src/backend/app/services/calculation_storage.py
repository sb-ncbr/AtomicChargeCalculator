import traceback
from sqlalchemy.orm import Session

from models.calculation import (
    CalculationConfigDto,
    CalculationResultDto,
    CalculationSetPreviewDto,
)
from models.paging import PagedList
from models.molecule_info import MoleculeSetStats
from db.schemas.calculation import (
    AdvancedSettings,
    CalculationConfig,
    CalculationSet,
    CalculationSetStats,
)
from db.schemas.stats import AtomTypeCount, MoleculeSetStats as MoleculeSetStatsModel

from db.repositories.calculation_config_repository import CalculationConfigRepository
from db.repositories.calculation_set_repository import (
    CalculationSetFilters,
    CalculationSetRepository,
)
from db.repositories.moleculeset_stats_repository import MoleculeSetStatsRepository

from models.setup import AdvancedSettingsDto, StoredSettingsDto
from db.repositories.advanced_settings_repository import AdvancedSettingsRepository
from db.database import SessionManager
from services.logging.base import LoggerBase


class CalculationStorageService:
    """Service for manipulating calculations in the database."""

    def __init__(
        self,
        logger: LoggerBase,
        set_repository: CalculationSetRepository,
        config_repository: CalculationConfigRepository,
        stats_repository: MoleculeSetStatsRepository,
        advanced_settings_repository: AdvancedSettingsRepository,
        session_manager: SessionManager,
    ):
        self.set_repository = set_repository
        self.config_repository = config_repository
        self.stats_repository = stats_repository
        self.advanced_settings_repository = advanced_settings_repository
        self.session_manager = session_manager
        self.logger = logger

    def get_info(self, session: Session, file_hash: str) -> MoleculeSetStats | None:
        # Getting info manually due to lazy loading issue

        info = self.stats_repository.get(session, file_hash)

        if info is None:
            return None

        info_dict = {
            "total_molecules": info.total_molecules,
            "total_atoms": info.total_atoms,
            "atom_type_counts": [vars(count) for count in info.atom_type_counts],
        }

        return MoleculeSetStats(info_dict)

    def get_calculations(
        self, filters: CalculationSetFilters
    ) -> PagedList[CalculationSetPreviewDto]:
        """Get calculations from database based on filters."""

        try:
            with self.session_manager.session() as session:
                self.logger.info("Getting calculations from database.")
                calculations_list = self.set_repository.get_all(session, filters)
                calculations_list.items = [
                    CalculationSetPreviewDto.model_validate(
                        {
                            "id": calculation_set.id,
                            "files": {
                                stats_assoc.file_name: self.get_info(
                                    session, stats_assoc.molecule_set_id
                                )
                                for stats_assoc in calculation_set.molecule_set_stats_associations
                            },
                            "configs": calculation_set.configs,
                            "settings": StoredSettingsDto.model_validate(
                                calculation_set.advanced_settings
                            ),
                            "created_at": calculation_set.created_at,
                        }
                    )
                    for calculation_set in calculations_list.items
                ]

            return PagedList[CalculationSetPreviewDto].model_validate(calculations_list)
        except Exception as e:
            self.logger.error(f"Error getting calculations from database: {traceback.format_exc()}")
            raise e

    def get_calculation_set(self, computation_id: str) -> CalculationSet | None:
        """Get calculation set from database."""

        try:
            self.logger.info(f"Getting calculation set {computation_id}.")
            with self.session_manager.session() as session:
                return self.set_repository.get(session, computation_id)
        except Exception as e:
            self.logger.error(
                f"Error getting calculation set {computation_id}: {traceback.format_exc()}"
            )
            raise e

    def store_file_info(self, file_hash: str, info: MoleculeSetStats) -> MoleculeSetStats:
        """Store file info to database."""

        try:
            with self.session_manager.session() as session:
                self.logger.info(f"Storing stats of file with hash '{file_hash}'.")
                info_model = MoleculeSetStatsModel(
                    file_hash=file_hash,
                    total_molecules=info.total_molecules,
                    total_atoms=info.total_atoms,
                    atom_type_counts=[
                        AtomTypeCount(symbol=count.symbol, count=count.count)
                        for count in info.atom_type_counts
                    ],
                )

                return self.stats_repository.store(session, info_model)
        except Exception as e:
            self.logger.error(
                f"Error storing stats of file with hash '{file_hash}': "
                + f"{traceback.format_exc()}"
            )
            raise e

    def store_calculation_results(
        self,
        computation_id: str,
        settings: AdvancedSettingsDto,
        results: list[CalculationResultDto],
        user_id: str | None,
    ) -> None:
        try:
            self.logger.info(f"Storing calculation results for computation {computation_id}.")

            with self.session_manager.session() as session:
                settings_entity = self._get_or_create_advanced_settings(session, settings)
                calculation_set = self._get_or_create_calculation_set(
                    session, computation_id, user_id, settings_entity
                )

                added_stats = set()

                # The computation keeps its configurations and files for the history. The
                # charges are in the computation's files; they are not stored or reused.
                for result in results:
                    if not result.calculations:
                        # No charges; the failure is reported with the computation.
                        continue

                    self._get_or_create_config(session, result.config, calculation_set)

                    files = {c.file_hash: c.file for c in result.calculations}
                    self._add_molecule_stats(session, calculation_set, files, added_stats)

                self.set_repository.store(session, calculation_set)

        except Exception as e:
            self.logger.error(
                f"Error storing calculation results for computation {computation_id}."
            )
            raise e

    def setup_calculation(
        self,
        computation_id: str,
        settings: AdvancedSettingsDto,
        file_hashes: list[str],
        user_id: str | None,
    ) -> None:
        """Setup calculation in database."""

        try:
            self.logger.info("Setting up calculation.")

            with self.session_manager.session() as session:
                settings_entity = self._get_or_create_advanced_settings(session, settings)

                calculation_set = CalculationSet(
                    id=computation_id,
                    user_id=user_id,
                    advanced_settings=settings_entity,
                )

                for file_hash in file_hashes:
                    calculation_set.molecule_set_stats.append(
                        self.stats_repository.get(session, file_hash)
                    )

                self.set_repository.store(session, calculation_set)
        except Exception as e:
            self.logger.error(f"Error setting up calculation: {traceback.format_exc()}")
            raise e

    def delete_calculation_set(self, computation_id: str) -> None:
        """Delete calculation set from database."""

        try:
            self.logger.info(f"Deleting calculation set {computation_id}.")
            with self.session_manager.session() as session:
                self.set_repository.delete(session, computation_id)
        except Exception as e:
            self.logger.error(
                f"Error deleting calculation set {computation_id}: {traceback.format_exc()}"
            )
            raise e

    def _get_or_create_advanced_settings(
        self, session: Session, settings: AdvancedSettingsDto
    ) -> AdvancedSettings:
        """Get existing settings or create new."""

        settings_entity = self.advanced_settings_repository.get(session, settings)
        if settings_entity is None:
            settings_entity = AdvancedSettings(
                selection=settings.selection,
                permissive_types=settings.permissive_types,
            )
            self.advanced_settings_repository.store(session, settings_entity)
        return settings_entity

    def _get_or_create_calculation_set(
        self,
        session: Session,
        computation_id: str,
        user_id: str | None,
        settings_entity: AdvancedSettings,
    ) -> CalculationSet:
        """Get existing calculation set or create new."""

        calculation_set = self.set_repository.get(session, computation_id)
        if calculation_set is None:
            calculation_set = CalculationSet(
                id=computation_id,
                user_id=user_id,
                advanced_settings=settings_entity,
            )
            self.set_repository.store(session, calculation_set)

        return calculation_set

    def _get_or_create_config(
        self, session: Session, config: CalculationConfigDto, calculation_set: CalculationSet
    ) -> CalculationConfig:
        """Get existing config or create new."""

        existing_config = self.config_repository.get(session, config.method, config.parameters)

        if existing_config is None:
            config_entity = CalculationConfig(method=config.method, parameters=config.parameters)
        else:
            config_entity = existing_config

        if config_entity not in calculation_set.configs:
            calculation_set.configs.append(config_entity)

        return config_entity

    def _add_molecule_stats(
        self,
        session: Session,
        calculation_set: CalculationSet,
        files: dict[str, str],
        added_stats: set[str],
    ) -> None:
        file_hashes = set(files.keys())
        new_file_hashes = file_hashes - added_stats

        for file_hash in new_file_hashes:
            stats = self.stats_repository.get(session, file_hash)

            if stats is None:
                # This should never happen
                continue

            association = CalculationSetStats(
                molecule_set_id=stats.file_hash,
                file_name=files.get(stats.file_hash),
            )
            calculation_set.molecule_set_stats_associations.append(association)
            added_stats.add(stats.file_hash)
