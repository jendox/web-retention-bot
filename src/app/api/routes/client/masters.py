from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import require_user
from app.models.user import User
from app.schemas.client import ClientMasterLinkUpdate, ClientMyMasterItem
from app.schemas.errors import ErrorDetail
from app.schemas.service import ServiceSchema
from app.use_cases.clients import (
    ListClientMastersUseCase,
    ListMasterServicesForClientUseCase,
    UpdateClientMasterLinkUseCase,
    get_list_client_masters_use_case,
    get_list_master_services_for_client_use_case,
    get_update_client_master_link_use_case,
)

router = APIRouter(prefix="/masters", tags=["client-masters"])


@router.get(
    "",
    summary="List masters linked to the current user as a client",
    description=(
        "Returns master profiles for every non-revoked master–client link where the client card "
        "belongs to the authenticated user. Independent of bookings."
    ),
    response_model=list[ClientMyMasterItem],
    status_code=status.HTTP_200_OK,
    response_description="Masters linked to the current user's client cards.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail, "description": "Missing or invalid session cookie."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail, "description": "Email not verified."},
    },
)
async def list_my_masters(
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[ListClientMastersUseCase, Depends(get_list_client_masters_use_case)],
) -> list[ClientMyMasterItem]:
    return await use_case(user.id)


@router.patch(
    "/{master_id}",
    summary="Update client-side label for a linked master",
    description=(
        "Updates the current client's private alias for a linked master. The master profile itself is unchanged."
    ),
    response_model=ClientMyMasterItem,
    status_code=status.HTTP_200_OK,
    response_description="Updated linked master item as shown in the client cabinet.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorDetail, "description": "Request body is invalid."},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail, "description": "Missing or invalid session cookie."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail, "description": "Email not verified."},
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "Master is not linked to this client."},
    },
)
async def patch_my_master_link(
    master_id: UUID,
    payload: ClientMasterLinkUpdate,
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[
        UpdateClientMasterLinkUseCase,
        Depends(get_update_client_master_link_use_case),
    ],
) -> ClientMyMasterItem:
    return await use_case(user, master_id, payload)


@router.get(
    "/{master_id}/services",
    summary="Active services for a linked master (client view)",
    description=(
        "Returns active bookable services for a master only when the current user is linked to that master as a "
        "client. Used before creating or rescheduling a client-side booking."
    ),
    response_model=list[ServiceSchema],
    status_code=status.HTTP_200_OK,
    response_description="Active services visible to this client.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail, "description": "Missing or invalid session cookie."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail, "description": "Email not verified."},
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "Not linked to this master."},
    },
)
async def list_master_services_for_client(
    master_id: UUID,
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[
        ListMasterServicesForClientUseCase,
        Depends(get_list_master_services_for_client_use_case),
    ],
) -> list[ServiceSchema]:
    return await use_case(user=user, master_id=master_id)
