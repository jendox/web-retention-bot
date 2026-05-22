from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.repositories.clients import ClientRepository, get_client_repo
from app.schemas.client import ClientProfileUpdate, ClientSchema
from app.use_cases.clients.exceptions import ClientNothingToUpdateError, ClientProfileNotFoundError

__all__ = ["UpdateClientProfileUseCase", "get_update_client_profile_use_case"]

logger = get_logger("app.client_profile")


class UpdateClientProfileUseCase:
    def __init__(self, client_repo: ClientRepository) -> None:
        self._client_repo = client_repo

    async def __call__(self, *, user_id: UUID, payload: ClientProfileUpdate) -> ClientSchema:
        with log_context(use_case="update_client_profile", user_id=str(user_id)):
            patch = payload.model_dump(exclude_unset=True)
            if not patch:
                logger.warning("failed", reason="empty_patch")
                raise ClientNothingToUpdateError()

            clients = await self._client_repo.list_client_profiles_for_user(user_id)
            if not clients:
                raise ClientProfileNotFoundError()

            for client in clients:
                client.apply_patch(patch)
            await self._client_repo.flush()

            primary = await self._client_repo.primary_client_profile_for_user(user_id)
            assert primary is not None
            logger.info("updated")
            return ClientSchema.model_validate(primary)


def get_update_client_profile_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
) -> UpdateClientProfileUseCase:
    return UpdateClientProfileUseCase(client_repo)
