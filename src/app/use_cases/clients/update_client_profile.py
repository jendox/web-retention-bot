from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends

from app.api.deps import require_user
from app.core.structured_logging import get_logger
from app.models.client import Client
from app.models.user import User
from app.repositories.clients import ClientRepository, get_client_repo
from app.schemas.client import ClientProfileUpdate, ClientSchema
from app.use_cases.clients.exceptions import ClientNothingToUpdateError, ClientProfileNotFoundError

__all__ = ["UpdateClientProfileUseCase", "get_update_client_profile_use_case"]

logger = get_logger("app.client_profile")

_NOT_NULLABLE_FIELDS = frozenset({"display_name"})


class UpdateClientProfileUseCase:
    def __init__(self, user: User, client_repo: ClientRepository) -> None:
        self._user = user
        self._client_repo = client_repo

    @staticmethod
    def _apply_patch(client: Client, patch: dict[str, Any]) -> None:
        for key, value in patch.items():
            if key in _NOT_NULLABLE_FIELDS and value is None:
                continue
            setattr(client, key, value)

    async def get_profile(self) -> ClientSchema:
        client = await self._client_repo.primary_client_profile_for_user(self._user.id)
        if client is None:
            raise ClientProfileNotFoundError()
        return ClientSchema.model_validate(client)

    async def __call__(self, payload: ClientProfileUpdate) -> ClientSchema:
        patch = payload.model_dump(exclude_unset=True)
        if not patch:
            logger.warning("failed", reason="empty_patch")
            raise ClientNothingToUpdateError()

        clients = await self._client_repo.list_client_profiles_for_user(self._user.id)
        if not clients:
            raise ClientProfileNotFoundError()

        for client in clients:
            client.apply_patch(patch)
        await self._client_repo.flush()

        primary = await self._client_repo.primary_client_profile_for_user(self._user.id)
        assert primary is not None
        return ClientSchema.model_validate(primary)


def get_update_client_profile_use_case(
    user: Annotated[User, Depends(require_user)],
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
) -> UpdateClientProfileUseCase:
    return UpdateClientProfileUseCase(user, client_repo)
