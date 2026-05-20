from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, status

from app.api.deps import require_user
from app.core.structured_logging import get_logger
from app.models.client import Client
from app.models.user import User
from app.repositories.clients import ClientRepository, get_client_repo
from app.schemas.client import ClientProfileUpdate, ClientSchema

__all__ = ["UpdateClientProfileUseCase", "get_update_client_profile_use_case"]

logger = get_logger("app.client_profile")

_NOT_NULLABLE_FIELDS = frozenset({"display_name"})


class UpdateClientProfileUseCase:
    def __init__(self, user: User, client_repo: ClientRepository) -> None:
        self._user = user
        self._client_repo = client_repo

    def _apply_patch(self, client: Client, patch: dict[str, Any]) -> None:
        for key, value in patch.items():
            if key in _NOT_NULLABLE_FIELDS and value is None:
                continue
            setattr(client, key, value)

    async def get_profile(self) -> ClientSchema:
        client = await self._client_repo.primary_client_profile_for_user(self._user.id)
        if client is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Client profile not found")
        return ClientSchema.model_validate(client)

    async def __call__(self, payload: ClientProfileUpdate) -> ClientSchema:
        patch = payload.model_dump(exclude_unset=True)
        if not patch:
            logger.warning("failed", reason="empty_patch")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No fields to update.")

        clients = await self._client_repo.list_client_profiles_for_user(self._user.id)
        if not clients:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Client profile not found")

        for client in clients:
            self._apply_patch(client, patch)
        await self._client_repo.flush()

        primary = await self._client_repo.primary_client_profile_for_user(self._user.id)
        assert primary is not None
        return ClientSchema.model_validate(primary)


def get_update_client_profile_use_case(
    user: Annotated[User, Depends(require_user)],
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
) -> UpdateClientProfileUseCase:
    return UpdateClientProfileUseCase(user, client_repo)
