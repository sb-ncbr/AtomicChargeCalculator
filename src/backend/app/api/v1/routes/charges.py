"""Charge calculation routes."""

import logging
import uuid


from typing import Annotated, Literal
from fastapi import (
    BackgroundTasks,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    status,
)
from fastapi.responses import FileResponse
from fastapi.routing import APIRouter
from dependency_injector.wiring import inject, Provide

from api.v1.exceptions import BadRequestError, NotFoundError
from api.v1.schemas.response import Response, ResponseError

from models.calculation import (
    CalculationConfigDto,
    CalculationResultDto,
    CalculationSetPreviewDto,
    CalculationState,
)
from models.method import Method
from models.molecule_info import MoleculeSetStats
from models.paging import PagedList
from models.parameters import Parameters
from models.suitable_methods import SuitableMethods

from db.repositories.calculation_set_repository import CalculationSetFilters

from api.v1.container import Container
from api.v1.schemas.charges import (
    BestParametersRequest,
    CalculateChargesRequest,
    SetupRequest,
    StatsRequest,
    SuitableMethodsRequest,
)

from models.setup import AdvancedSettingsDto

from services.calculation_storage import CalculationStorageService
from services.mmcif import MmCIFService
from services.io import IOService
from services.chargefw2 import ChargeFW2Service

charges_router = APIRouter(prefix="/charges", tags=["charges"])


# --- Public API handlers ---


@charges_router.get("/methods/available")
@inject
async def available_methods(
    chargefw2: ChargeFW2Service = Depends(Provide[Container.chargefw2_service]),
) -> Response[list[Method]]:
    """Returns the list of available methods for charge calculation."""

    try:
        methods = chargefw2.get_available_methods()
        return Response[list[Method]](data=methods)
    except Exception as e:
        raise BadRequestError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error getting available methods.",
        ) from e


@charges_router.post("/methods/suitable")
@inject
async def suitable_methods(
    request: Request,
    data: SuitableMethodsRequest,
    chargefw2: ChargeFW2Service = Depends(Provide[Container.chargefw2_service]),
) -> Response[SuitableMethods]:
    """
    Returns suitable methods for the provided computation.

        fileHashes: List of file hashes to get suitable methods for.
        permissiveTypes: Use similar parameters for similar atom/bond types if no exact match is found.
    """
    user_id = str(request.state.user.id) if request.state.user is not None else None

    try:
        suitable = await chargefw2.get_suitable_methods(
            data.file_hashes, data.permissive_types, user_id
        )
        return Response(data=suitable)
    except Exception as e:
        raise BadRequestError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error getting suitable methods.",
        ) from e


@charges_router.get(
    "/parameters/{method_name}/available",
    responses={
        404: {
            "description": "Method not found.",
            "model": ResponseError,
            "content": {
                "application/json": {
                    "example": {"success": False, "message": "Method not found."}
                }
            },
        },
        400: {
            "description": "Error getting available parameters.",
            "model": ResponseError,
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Error getting available parameters.",
                    }
                }
            },
        },
    },
)
@inject
async def available_parameters(
    method_name: Annotated[
        str,
        Path(
            description="""
            Method name to get parameters for. 
            One of the available methods (list can be received from GET "/api/v1/methods/available").
            """
        ),
    ],
    chargefw2: ChargeFW2Service = Depends(Provide[Container.chargefw2_service]),
) -> Response[list[Parameters]]:
    """Returns the list of available parameters for the provided method."""

    methods = chargefw2.get_available_methods()
    if not any(method.internal_name == method_name for method in methods):
        raise BadRequestError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Method '{method_name}' not found.",
        )

    try:
        parameters = await chargefw2.get_available_parameters(method_name)
        return Response[list[Parameters]](data=parameters)
    except Exception as e:
        raise BadRequestError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error getting available parameters for method '{method_name}'.",
        ) from e


@charges_router.post(
    "/parameters/best",
    responses={
        404: {
            "description": "Method not found.",
            "model": ResponseError,
            "content": {
                "application/json": {
                    "example": {"success": False, "message": "Method not found."}
                }
            },
        },
        400: {
            "description": "Error getting best parameters.",
            "model": ResponseError,
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Error getting best parameters.",
                    }
                }
            },
        },
    },
)
@inject
async def best_parameters(
    data: BestParametersRequest,
    chargefw2: ChargeFW2Service = Depends(Provide[Container.chargefw2_service]),
    io_service: IOService = Depends(Provide[Container.io_service]),
) -> Response[Parameters]:
    """
    Returns the best parameters for the provided method and file.

        methodName: Method name to get the best parameters for.
        fileHash: File hashes to get suitable methods for.
        permissiveTypes: Use similar parameters for similar atom/bond types if no exact match is found.
    """

    methods = chargefw2.get_available_methods()
    if not any(method.internal_name == data.method_name for method in methods):
        raise BadRequestError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Method '{data.method_name}' not found.",
        )

    file_path = io_service.get_filepath(data.file_hash)

    if file_path is None:
        raise BadRequestError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{data.file_hash}' not found.",
        )

    try:
        parameters = await chargefw2.get_best_parameters(
            data.method_name, file_path, data.permissive_types
        )
        return Response[Parameters](data=parameters)
    except Exception as e:
        raise BadRequestError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error getting best parameters for method '{data.method_name}'.",
        ) from e


@charges_router.post(
    "/stats",
    responses={
        404: {
            "description": "File not found.",
            "model": ResponseError,
            "content": {
                "application/json": {
                    "example": {"success": False, "message": "File not found."}
                }
            },
        },
        400: {
            "description": "Error getting file information.",
            "model": ResponseError,
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Error getting file information.",
                    }
                }
            },
        },
    },
)
@inject
async def info(
    request: Request,
    data: StatsRequest,
    chargefw2: ChargeFW2Service = Depends(Provide[Container.chargefw2_service]),
    io_service: IOService = Depends(Provide[Container.io_service]),
) -> Response[MoleculeSetStats]:
    """
    Returns information about the provided file.
    Number of molecules, total atoms and individual atoms.

        fileHash: File hashes to get suitable methods for.
    """

    user_id = str(request.state.user.id) if request.state.user is not None else None

    try:
        filepath = io_service.get_filepath(data.file_hash, user_id)

        if filepath is None:
            raise FileNotFoundError()

        info_data = await chargefw2.info(filepath)

        return Response(data=info_data)
    except FileNotFoundError as e:
        raise NotFoundError(detail="File not found.") from e
    except Exception as e:
        raise BadRequestError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error getting file information.",
        ) from e


@charges_router.post(
    "/calculate",
    responses={
        200: {
            "description": "Charges calculated successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "computationId": "0b9ee9e0-bd69-409d-a3af-3bf11666ee86",
                            "results": [
                                {
                                    "calculations": [
                                        {
                                            "file": "file_name.cif",
                                            "fileHash": "4d689a346c6e852f21e3083025d827d7ba165c7c468d8a3c970216e9365fb3bd",
                                            "charges": {
                                                "molecule1": [0.1, 0.2],
                                                "molecule2": [0.3, 0.4],
                                            },
                                            "config": {
                                                "method": "sqeqp",
                                                "parameters": "SQEqp_10_Schindler2021_CCD_gen",
                                            },
                                        }
                                    ],
                                }
                            ],
                        },
                    }
                }
            },
        },
        413: {
            "description": "Unable to calculate charges. Calculation is too large.",
            "model": ResponseError,
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Unable to calculate charges. Calculation is too large.",
                    }
                }
            },
        },
        400: {
            "description": "No files provided.",
            "model": ResponseError,
            "content": {
                "application/json": {
                    "example": {"success": False, "message": "No files provided."}
                }
            },
        },
    },
)
@inject
async def calculate_charges(
    request: Request,
    data: CalculateChargesRequest,
    background_tasks: BackgroundTasks,
    response_format: Annotated[
        Literal["charges", "none"], Query(description="Output format.")
    ] = "charges",
    chargefw2: ChargeFW2Service = Depends(Provide[Container.chargefw2_service]),
    storage_service: CalculationStorageService = Depends(
        Provide[Container.storage_service]
    ),
    mmcif_service: MmCIFService = Depends(Provide[Container.mmcif_service]),
    io_service: IOService = Depends(Provide[Container.io_service]),
):
    """
    Calculates partial atomic charges for files in the provided directory.
    Returns a list of dictionaries with charges (decimal numbers).
    If no config is provided, the most suitable method and its parameters will be used.

        configs: List of combinations of suitable methods and parameters.
        fileHashes: List of file hashes to calculate charges for.
        response_format:
            Charges: returns a list of charges once it is finished.
            None: immediately returns computation id - you can then use /<computation_id>/status endpoint to check the state and download files once it's completed.

    settings:

        readHetatm: Read HETATM records from PDB/mmCIF files.
        ignoreWater: Discard water molecules from PDB/mmCIF files.
        permissiveTypes: Use similar parameters for similar atom/bond types if no exact match is found.

    """

    user_id = str(request.state.user.id) if request.state.user is not None else None

    if user_id is not None:
        _, available_b, quota_b = io_service.get_quota(user_id)
        if available_b <= 0:
            quota_mb = quota_b / 1024 / 1024
            raise BadRequestError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unable to calculate charges. Quota exceeded. "
                + f"Maximum storage space is {quota_mb} MB.",
            )

    computation_id = data.computation_id or str(uuid.uuid4())
    calculation_set = storage_service.get_calculation_set(computation_id)

    if not data.file_hashes and calculation_set is None:
        # if no file hashes were provided and computation has not been set up
        raise BadRequestError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file hashes provided.",
        )

    settings = (
        calculation_set.advanced_settings
        if calculation_set is not None
        else data.settings
    )

    if settings is None:
        settings = AdvancedSettingsDto()

    try:
        io_service.prepare_inputs(user_id, computation_id, data.file_hashes)

        file_hashes = data.file_hashes
        if not file_hashes:
            # get all files if non provided and computation has already been set up
            inputs_path = io_service.get_inputs_path(computation_id, user_id)
            file_hashes = [
                io_service.parse_filename(file)[0]
                for file in io_service.listdir(inputs_path)
            ]

        if not file_hashes:
            # no files found and provided
            raise BadRequestError(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file hashes provided.",
            )

        file_hashes = list(set(file_hashes))

        total_size = sum(
            io_service.get_file_size(file_hash, user_id) or 0
            for file_hash in file_hashes
        )

        if total_size > io_service.max_file_size:
            max_file_size_mb = io_service.max_file_size / 1024 / 1024
            raise BadRequestError(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Unable to calculate charges. Calculation is too large. "
                + f"Maximum allowed size is {max_file_size_mb} MB.",
            )

        configs = data.configs
        if not configs:
            # use most suitable method and parameters if none provided
            suitable = await chargefw2.get_computation_suitable_methods(
                computation_id, user_id
            )

            if len(suitable.methods) == 0:
                raise BadRequestError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No suitable methods found.",
                )

            method_name = suitable.methods[0].internal_name
            parameters = suitable.parameters.get(method_name, [])
            parameters_name = (
                parameters[0].internal_name if len(parameters) > 0 else None
            )

            configs = [
                CalculationConfigDto(method=method_name, parameters=parameters_name)
            ]

        io_service.change_computation_state(
            user_id, computation_id, CalculationState.CALCULATING
        )

        if response_format == "none":
            background_tasks.add_task(
                _calculate_charges,
                computation_id,
                file_hashes,
                settings,
                configs,
                user_id,
                chargefw2,
                storage_service,
                mmcif_service,
                io_service,
            )

            return Response(data=computation_id)

        calculations = await _calculate_charges(
            computation_id,
            file_hashes,
            settings,
            configs,
            user_id,
            chargefw2,
            storage_service,
            mmcif_service,
            io_service,
        )

        return Response(data={"computationId": computation_id, "results": calculations})
    except BadRequestError as e:
        raise e
    except Exception as e:
        raise BadRequestError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error calculating charges. {str(e)}",
        ) from e


@charges_router.get("/{computation_id}/status")
@inject
async def get_calculation_status(
    request: Request,
    computation_id: Annotated[str, Path(description="UUID of the computation.")],
    io: IOService = Depends(Provide[Container.io_service]),
) -> Response[dict]:
    """Returns the status of a computation."""
    user_id = str(request.state.user.id) if request.state.user is not None else None

    try:
        state, note = io.get_computation_state(user_id, computation_id)

        if state is CalculationState.FAILED:
            return Response(data={"status": state.name, "error": note})

        return Response(data={"status": state.name})
    except Exception:
        return Response(data={"status": "UNKNOWN"})


# --- Route handlers used by ACC III Web ---


@charges_router.post("/{computation_id}/methods/suitable", include_in_schema=False)
@inject
async def computation_suitable_methods(
    request: Request,
    computation_id: Annotated[str, Path(description="UUID of the computation.")],
    chargefw2: ChargeFW2Service = Depends(Provide[Container.chargefw2_service]),
) -> Response[SuitableMethods]:
    """Returns suitable methods for the provided computation."""
    user_id = str(request.state.user.id) if request.state.user is not None else None

    try:
        data = await chargefw2.get_computation_suitable_methods(
            computation_id,
            user_id,
        )
        return Response(data=data)
    except Exception as e:
        raise BadRequestError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error getting suitable methods.",
        ) from e


@charges_router.post("/setup", include_in_schema=False)
@inject
async def setup(
    request: Request,
    config: SetupRequest,
    io_service: IOService = Depends(Provide[Container.io_service]),
    storage_service: CalculationStorageService = Depends(
        Provide[Container.storage_service]
    ),
):
    """Prepares input for computation so it can be run later."""

    user_id = str(request.state.user.id) if request.state.user is not None else None

    if user_id is not None:
        _, available_b, quota_b = io_service.get_quota(user_id)
        if available_b <= 0:
            quota_mb = quota_b / 1024 / 1024
            raise BadRequestError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unable to set up calculation. Quota would be exceeded. "
                + f"Maximum storage space is {quota_mb} MB.",
            )

    total_size = sum(
        io_service.get_file_size(file_hash, user_id) or 0
        for file_hash in config.file_hashes
    )

    if total_size > io_service.max_file_size:
        max_file_size_mb = io_service.max_file_size / 1024 / 1024
        raise BadRequestError(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Unable to set up calculation. Calculation is too large. "
            + f"Maximum allowed size is {max_file_size_mb} MB.",
        )

    computation_id = str(uuid.uuid4())

    if config.settings is None:
        config.settings = AdvancedSettingsDto()

    try:
        io_service.prepare_inputs(user_id, computation_id, config.file_hashes)
        storage_service.setup_calculation(
            computation_id, config.settings, config.file_hashes, user_id
        )
        return Response(data=computation_id)
    except Exception as e:
        raise BadRequestError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error setting up calculation.",
        ) from e


# chemical/x-cif
@charges_router.get("/{computation_id}/mmcif", include_in_schema=False)
@inject
async def get_mmcif(
    request: Request,
    computation_id: Annotated[str, Path(description="UUID of the computation.")],
    molecule: Annotated[str | None, Query(description="Molecule name.")] = None,
    io: IOService = Depends(Provide[Container.io_service]),
    mmcif_service: MmCIFService = Depends(Provide[Container.mmcif_service]),
    storage_service: CalculationStorageService = Depends(
        Provide[Container.storage_service]
    ),
) -> FileResponse:
    """Returns a mmcif file for the provided molecule in the computation."""

    user_id = str(request.state.user.id) if request.state.user is not None else None

    # this is a workaround because molstar is not able to send cookies when fetching mmcif
    set_exists = storage_service.get_calculation_set(computation_id)
    if set_exists is not None and set_exists.user_id is not None:
        user_id = str(set_exists.user_id)

    try:
        charges_path = io.get_charges_path(computation_id, user_id)
        mmcif_path = mmcif_service.get_molecule_mmcif(charges_path, molecule)
        return FileResponse(path=mmcif_path)
    except FileNotFoundError as e:
        raise NotFoundError(
            detail=f"MMCIF file for molecule '{molecule}' not found."
        ) from e
    except Exception as e:
        raise BadRequestError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Something went wrong while getting MMCIF data.",
        ) from e


@charges_router.get("/examples/{example_id}/mmcif", include_in_schema=False)
@inject
async def get_example_mmcif(
    example_id: Annotated[
        str, Path(description="ID of the example.", example="phenols")
    ],
    molecule: Annotated[str | None, Query(description="Molecule name.")] = None,
    io: IOService = Depends(Provide[Container.io_service]),
    mmcif_service: MmCIFService = Depends(Provide[Container.mmcif_service]),
) -> FileResponse:
    """Returns a mmcif file for the provided molecule in the example."""
    try:
        examples_path = io.get_example_path(example_id)
        mmcif_path = mmcif_service.get_molecule_mmcif(examples_path, molecule)
        return FileResponse(path=mmcif_path)
    except FileNotFoundError as e:
        raise NotFoundError(
            detail=f"MMCIF file for molecule '{molecule}' in example '{example_id}' not found."
        ) from e
    except Exception as e:
        raise BadRequestError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Something went wrong while getting MMCIF data.",
        ) from e


@charges_router.get("/{computation_id}/molecules", include_in_schema=False)
@inject
async def get_molecules(
    request: Request,
    computation_id: Annotated[str, Path(description="UUID of the computation.")],
    io: IOService = Depends(Provide[Container.io_service]),
    chargefw2: ChargeFW2Service = Depends(Provide[Container.chargefw2_service]),
) -> Response[list[str]]:
    """Returns the list of molecules in the provided computation."""
    user_id = str(request.state.user.id) if request.state.user is not None else None

    try:
        charges_path = io.get_charges_path(computation_id, user_id)
        molecules = chargefw2.get_calculation_molecules(charges_path)
        return Response(data=sorted(molecules))
    except FileNotFoundError as e:
        raise NotFoundError(detail=f"Computation '{computation_id}' not found.") from e
    except Exception as e:
        raise BadRequestError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Something went wrong while getting molecules.",
        ) from e


@charges_router.get("/examples/{example_id}/molecules", include_in_schema=False)
@inject
async def get_example_molecules(
    example_id: Annotated[
        str, Path(description="Id of the example.", example="phenols")
    ],
    io: IOService = Depends(Provide[Container.io_service]),
    chargefw2: ChargeFW2Service = Depends(Provide[Container.chargefw2_service]),
) -> Response[list[str]]:
    """Returns the list of molecules in the provided computation."""
    try:
        charges_path = io.get_example_path(example_id)
        molecules = chargefw2.get_calculation_molecules(charges_path)
        return Response(data=sorted(molecules))
    except FileNotFoundError as e:
        raise NotFoundError(detail=f"Example '{example_id}' not found.") from e
    except Exception as e:
        raise BadRequestError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Something went wrong while getting molecules.",
        ) from e


@charges_router.get("/calculations", include_in_schema=False)
@inject
async def get_calculations(
    request: Request,
    page: Annotated[int, Query(description="Page number.")] = 1,
    page_size: Annotated[int, Query(description="Number of items per page.")] = 10,
    order_by: Annotated[
        Literal["created_at"], Query(description="Order by field.")
    ] = "created_at",
    order: Annotated[
        Literal["asc", "desc"], Query(description="Order direction.")
    ] = "desc",
    storage_service: CalculationStorageService = Depends(
        Provide[Container.storage_service]
    ),
) -> Response[PagedList[CalculationSetPreviewDto]]:
    """Returns all calculations stored in the database."""
    user_id = str(request.state.user.id) if request.state.user is not None else None

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You need to be logged in to get calculations.",
        )

    try:
        filters = CalculationSetFilters(
            order=order,
            order_by=order_by,
            page=page,
            page_size=page_size,
            user_id=user_id,
        )
        calculations = storage_service.get_calculations(filters)
        return Response(data=calculations)
    except Exception as e:
        raise BadRequestError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error getting calculations.",
        ) from e


@charges_router.delete("/{computation_id}", include_in_schema=False)
@inject
async def delete_calculation(
    request: Request,
    computation_id: Annotated[str, Path(description="UUID of the computation.")],
    chargefw2: ChargeFW2Service = Depends(Provide[Container.chargefw2_service]),
    storage_service: CalculationStorageService = Depends(
        Provide[Container.storage_service]
    ),
) -> Response[None]:
    """Deletes the computation."""
    user_id = str(request.state.user.id) if request.state.user is not None else None

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You need to be logged in to delete calculations.",
        )

    exists = storage_service.get_calculation_set(computation_id)

    if not exists or str(exists.user_id) != user_id:
        raise NotFoundError(detail="Computation not found.")

    try:
        chargefw2.delete_calculation(computation_id, user_id)
        return Response(data=None)
    except Exception as e:
        raise BadRequestError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Something went wrong while deleting computation.",
        ) from e


# --- Auxiliary functions ---


async def _calculate_charges(
    computation_id: str,
    file_hashes: list[str],
    settings: AdvancedSettingsDto,
    configs: list[CalculationConfigDto],
    user_id: str | None,
    chargefw2: ChargeFW2Service,
    storage_service: CalculationStorageService,
    mmcif_service: MmCIFService,
    io_service: IOService,
) -> list[CalculationResultDto]:
    """Runs the charge calculation and waits for results."""

    try:
        to_calculate, cached = storage_service.filter_existing_calculations(
            settings, file_hashes, configs
        )
        calculations = await chargefw2.calculate_charges(
            computation_id,
            settings,
            to_calculate,
            user_id,
        )

        for result in calculations:
            if result.config in cached:
                result.calculations.extend(cached[result.config])

        calculations.extend(
            [
                CalculationResultDto(config=config, calculations=results)
                for config, results in cached.items()
            ]
        )

        await _save_calculation_results(
            computation_id,
            settings,
            calculations,
            user_id,
            storage_service,
            chargefw2,
            mmcif_service,
            io_service,
        )

        io_service.change_computation_state(
            user_id, computation_id, CalculationState.COMPLETED
        )

        return calculations
    except Exception as e:
        io_service.change_computation_state(
            user_id, computation_id, CalculationState.FAILED, str(e)
        )


async def _save_calculation_results(
    computation_id: str,
    settings: AdvancedSettingsDto,
    calculations: list[CalculationResultDto],
    user_id: str | None,
    storage_service: CalculationStorageService,
    chargefw2: ChargeFW2Service,
    mmcif_service: MmCIFService,
    io_service: IOService,
) -> None:
    """Saves calculation results to storage and generates mmCIF files."""

    storage_service.store_calculation_results(
        computation_id, settings, calculations, user_id
    )
    await chargefw2.save_charges(settings, computation_id, calculations, user_id)
    _ = mmcif_service.write_to_mmcif(user_id, computation_id, calculations)

    if user_id is None:
        io_service.free_guest_compute_space()
