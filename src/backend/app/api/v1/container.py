"""Dependency injection container."""

import os

from dependency_injector import containers, providers
from dotenv import load_dotenv, find_dotenv


from db.database import Database, SessionManager
from db.repositories import advanced_settings_repository
from db.repositories.calculation_config_repository import CalculationConfigRepository
from db.repositories.calculation_set_repository import CalculationSetRepository
from db.repositories.user_repository import UserRepository
from db.repositories.moleculeset_stats_repository import MoleculeSetStatsRepository

from integrations.chargefw.chargefw import ChargeFWLocal
from integrations.io.io import IOLocal

from services.calculation_storage import CalculationStorageService
from services.charges import ChargeService
from services.file_storage import FileStorageService
from services.io import IOService
from services.logging.file_logger import FileLogger
from services.mmcif import MmCIFService
from services.oidc import OIDCService


load_dotenv(find_dotenv())


class Container(containers.DeclarativeContainer):
    """IoC container for the application."""

    wiring_config = containers.WiringConfiguration(packages=["api", "services"])

    # integrations
    charge_engine = providers.Singleton(ChargeFWLocal)
    io = providers.Singleton(IOLocal)

    # database
    db = providers.Singleton(Database, db_url=os.environ.get("ACC_DB_URL"))
    session_manager = providers.Singleton(
        SessionManager, session_factory=db.provided.session_factory
    )

    # repositories
    set_repository = providers.Factory(CalculationSetRepository)
    config_repository = providers.Factory(
        CalculationConfigRepository, set_repository=set_repository
    )
    user_repository = providers.Factory(UserRepository, session_manager=session_manager)
    stats_repository = providers.Factory(MoleculeSetStatsRepository)
    advanced_settings_repository = providers.Factory(
        advanced_settings_repository.AdvancedSettingsRepository,
    )

    # services
    logger_service = providers.Singleton(FileLogger)
    io_service = providers.Singleton(IOService, logger=logger_service, io=io)
    mmcif_service = providers.Singleton(MmCIFService, logger=logger_service, io=io_service)
    storage_service = providers.Singleton(
        CalculationStorageService,
        logger=logger_service,
        set_repository=set_repository,
        config_repository=config_repository,
        stats_repository=stats_repository,
        advanced_settings_repository=advanced_settings_repository,
        session_manager=session_manager,
    )
    file_storage_service = providers.Singleton(
        FileStorageService,
        logger=logger_service,
        io=io_service,
        session_manager=session_manager,
        storage_service=storage_service,
    )
    charge_service = providers.Singleton(
        ChargeService,
        engine=charge_engine,
        logger=logger_service,
        io=io_service,
        mmcif_service=mmcif_service,
        calculation_storage=storage_service,
        max_workers=int(os.environ.get("ACC_MAX_WORKERS") or 8),
        max_concurrent_calculations=int(os.environ.get("ACC_MAX_CONCURRENT_CALCULATIONS") or 3),
    )
    oidc_service = providers.Singleton(OIDCService, logger=logger_service)
