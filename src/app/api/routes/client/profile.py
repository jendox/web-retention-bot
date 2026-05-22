from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import require_user
from app.models.user import User
from app.schemas.client import ClientProfileUpdate, ClientSchema
from app.schemas.errors import ErrorDetail
from app.use_cases.clients import (
    GetClientProfileUseCase,
    UpdateClientProfileUseCase,
    get_get_client_profile_use_case,
    get_update_client_profile_use_case,
)

router = APIRouter(prefix="/profile", tags=["client-profile"])


@router.get(
    "",
    response_model=ClientSchema,
    summary="Current client profile",
    description=(
        "Returns the primary client card linked to the authenticated user. "
        "404 when the user has no client profile yet (e.g. before accepting an invitation)."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail},
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail},
    },
)
async def get_my_client_profile(
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[GetClientProfileUseCase, Depends(get_get_client_profile_use_case)],
) -> ClientSchema:
    return await use_case(user.id)


@router.patch(
    "",
    response_model=ClientSchema,
    summary="Update client profile",
    description=(
        "Updates display name and phone on every client card linked to the current user "
        "(keeps data consistent across masters)."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorDetail},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail},
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail},
    },
)
async def patch_my_client_profile(
    payload: ClientProfileUpdate,
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[UpdateClientProfileUseCase, Depends(get_update_client_profile_use_case)],
) -> ClientSchema:
    return await use_case(user_id=user.id, payload=payload)
