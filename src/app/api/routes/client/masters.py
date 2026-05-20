from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user
from app.core.database import get_db_session
from app.models.user import User
from app.repositories.clients import ClientRepository
from app.schemas.client import ClientMasterLinkUpdate, ClientMyMasterItem
from app.schemas.client_master import client_master_item
from app.schemas.errors import ErrorDetail
from app.schemas.service import ServiceSchema
from app.use_cases.clients.exceptions import (
    ClientMasterLinkError,
    ClientNothingToUpdateError,
)
from app.use_cases.clients.list_master_services import (
    ListMasterServicesForClientUseCase,
    get_list_master_services_for_client_use_case,
)
from app.use_cases.clients.update_client_master_link import (
    UpdateClientMasterLinkUseCase,
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
)
async def list_my_masters(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(require_user)],
) -> list[ClientMyMasterItem]:
    repo = ClientRepository(session)
    rows = await repo.list_masters_for_user_clients(user.id)
    return [
        client_master_item(
            master,
            link,
            client_id=client.id,
            client_display_name=client.display_name,
        )
        for master, link, client in rows
    ]


@router.patch(
    "/{master_id}",
    summary="Update client-side label for a linked master",
    response_model=ClientMyMasterItem,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorDetail},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail},
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail},
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
    try:
        return await use_case(user, master_id, payload)
    except ClientNothingToUpdateError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No fields to update.") from None
    except ClientMasterLinkError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.error_message) from None


@router.get(
    "/{master_id}/services",
    summary="Active services for a linked master (client view)",
    response_model=list[ServiceSchema],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail},
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
    try:
        return await use_case(user, master_id)
    except ClientMasterLinkError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.error_message) from None
