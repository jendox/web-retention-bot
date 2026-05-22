from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import require_master_profile
from app.core.pagination import Pagination, get_pagination
from app.models.master import MasterProfile
from app.schemas.client import ClientCreate, ClientUpdate, ClientWithLinkResponse
from app.schemas.errors import ErrorDetail
from app.schemas.pagination import PaginatedResponse
from app.use_cases.clients.create_client import CreateClientUseCase, get_create_client_use_case
from app.use_cases.clients.delete_client import DeleteClientUseCase, get_delete_client_use_case
from app.use_cases.clients.get_client import GetClientUseCase, get_get_client_use_case
from app.use_cases.clients.list_clients import ListClientsUseCase, get_list_clients_use_case
from app.use_cases.clients.update_client import UpdateClientUseCase, get_update_client_use_case

router = APIRouter(prefix="/clients", tags=["master-clients"])


@router.get(
    path="",
    summary="List clients for the current master",
    description=(
        "Returns clients linked to the authenticated master profile (paginated), with per-master alias, notes, "
        "and invitation status. Sort order: display name (case-insensitive), then client id."
    ),
    response_model=PaginatedResponse[ClientWithLinkResponse],
    response_description="Page of linked clients plus total count for the same filter.",
)
async def list_clients(
    pagination: Annotated[Pagination, Depends(get_pagination)],
    use_case: Annotated[ListClientsUseCase, Depends(get_list_clients_use_case)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
    q: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=100,
            description="Optional search by client name, alias, phone, email, or linked account email.",
        ),
    ] = None,
) -> PaginatedResponse[ClientWithLinkResponse]:
    return await use_case(master.id, pagination, search=q)


@router.post(
    path="",
    summary="Create a manual client card",
    description=(
        "Creates a client record and a master–client link without an app login (invitation flow is separate). "
        "Optional phone and email are stored as given; email is normalized to lowercase."
    ),
    status_code=status.HTTP_201_CREATED,
    response_model=ClientWithLinkResponse,
    response_description="New client and link; same shape as list items.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorDetail,
            "description": "Session missing or invalid (handled by dependency).",
        },
    },
)
async def add_client(
    payload: ClientCreate,
    use_case: Annotated[CreateClientUseCase, Depends(get_create_client_use_case)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> ClientWithLinkResponse:
    return await use_case(payload, master.id)


@router.get(
    path="/{client_id}",
    summary="Get one linked client",
    description=(
        "Fetches a single client only if it is linked to the current master. Use for the client detail / edit screen."
    ),
    response_model=ClientWithLinkResponse,
    response_description="Client profile and master-specific alias, notes, and link status.",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "No such client or it is not linked to this master.",
        },
    },
)
async def get_client(
    client_id: UUID,
    use_case: Annotated[GetClientUseCase, Depends(get_get_client_use_case)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> ClientWithLinkResponse:
    return await use_case(master.id, client_id)


@router.patch(
    path="/{client_id}",
    summary="Update client and master link fields",
    description=(
        "Partial update: send only fields to change. Core client fields (name, phone, email) and master-only "
        "fields (alias, notes) are applied in one request."
    ),
    response_model=ClientWithLinkResponse,
    response_description="Updated client and link snapshot.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorDetail,
            "description": "Request body omitted all updatable fields.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "No such client or it is not linked to this master.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorDetail,
            "description": "Linked client account fields cannot be changed.",
        },
    },
)
async def patch_client(
    client_id: UUID,
    payload: ClientUpdate,
    use_case: Annotated[UpdateClientUseCase, Depends(get_update_client_use_case)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> ClientWithLinkResponse:
    return await use_case(master_id=master.id, client_id=client_id, payload=payload)


@router.delete(
    path="/{client_id}",
    summary="Delete a client card",
    description=(
        "Removes the client row when there are no bookings and no invitation points at this client via "
        "`linked_client_id`. Otherwise responds with 409 so data stays consistent."
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Client removed; no response body.",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "No such client or it is not linked to this master.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorDetail,
            "description": "Client has bookings or is referenced by an invitation link.",
        },
    },
)
async def delete_client(
    client_id: UUID,
    use_case: Annotated[DeleteClientUseCase, Depends(get_delete_client_use_case)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> Response:
    await use_case(master_id=master.id, client_id=client_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
