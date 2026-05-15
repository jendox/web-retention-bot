from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.deps import require_master_profile
from app.core.pagination import Pagination, get_pagination
from app.models.master import MasterProfile
from app.schemas.errors import ErrorDetail
from app.schemas.pagination import PaginatedResponse
from app.schemas.service import ServiceCreate, ServiceOut, ServiceUpdate
from app.use_cases.services.create_service import CreateServiceUseCase, get_create_service_use_case
from app.use_cases.services.delete_service import DeleteServiceUseCase, get_delete_service_use_case
from app.use_cases.services.exceptions import ServiceHasBookingsError, ServiceNotFoundError
from app.use_cases.services.get_service import GetServiceUseCase, get_get_service_use_case
from app.use_cases.services.list_services import ListServicesUseCase, get_list_services_use_case
from app.use_cases.services.update_service import UpdateServiceUseCase, get_update_service_use_case

router = APIRouter(prefix="/services", tags=["services"])


@router.get(
    "",
    summary="List services for the current master",
    description=(
        "Paginated catalogue of services. Optional `is_active` filters by availability. "
        "Sort: `sort_order`, then creation time."
    ),
    response_model=PaginatedResponse[ServiceOut],
    response_description="Page of services and total count for the same filter.",
)
async def list_services(
    pagination: Annotated[Pagination, Depends(get_pagination)],
    use_case: Annotated[ListServicesUseCase, Depends(get_list_services_use_case)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
    is_active: Annotated[
        bool | None,
        Query(description="If true/false, only active / only inactive; omit for all."),
    ] = None,
) -> PaginatedResponse[ServiceOut]:
    return await use_case(master, pagination, is_active=is_active)


@router.post(
    "",
    summary="Create a service",
    description=(
        "Adds a bookable service. If `currency` is omitted, the master's default currency from the profile is used."
    ),
    response_model=ServiceOut,
    status_code=status.HTTP_201_CREATED,
    response_description="New service row.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorDetail,
            "description": "Session missing or invalid.",
        },
    },
)
async def post_service(
    payload: ServiceCreate,
    use_case: Annotated[CreateServiceUseCase, Depends(get_create_service_use_case)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> ServiceOut:
    return await use_case.execute(master, payload)


@router.get(
    "/{service_id}",
    summary="Get one service",
    description="Returns a service owned by the authenticated master.",
    response_model=ServiceOut,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "Not found or not owned by this master.",
        },
    },
)
async def get_service(
    service_id: UUID,
    use_case: Annotated[GetServiceUseCase, Depends(get_get_service_use_case)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> ServiceOut:
    try:
        return await use_case.execute(master, service_id)
    except ServiceNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Service not found.") from None


@router.patch(
    "/{service_id}",
    summary="Update a service",
    description="Partial update of service fields.",
    response_model=ServiceOut,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "Not found or not owned by this master.",
        },
    },
)
async def patch_service(
    service_id: UUID,
    payload: ServiceUpdate,
    use_case: Annotated[UpdateServiceUseCase, Depends(get_update_service_use_case)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> ServiceOut:
    try:
        return await use_case.execute(master, service_id, payload)
    except ServiceNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Service not found.") from None


@router.delete(
    "/{service_id}",
    summary="Delete a service",
    description="Removes the service if it has no bookings; otherwise 409.",
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Service removed.",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "Not found or not owned by this master.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorDetail,
            "description": "Service already has bookings.",
        },
    },
)
async def delete_service_route(
    service_id: UUID,
    use_case: Annotated[DeleteServiceUseCase, Depends(get_delete_service_use_case)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> Response:
    try:
        await use_case.execute(master, service_id)
    except ServiceNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Service not found.") from None
    except ServiceHasBookingsError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Service has bookings and cannot be deleted.",
        ) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
