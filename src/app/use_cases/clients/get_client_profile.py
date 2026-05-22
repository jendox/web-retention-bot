from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.repositories.clients import ClientRepository, get_client_repo
from app.schemas.client import ClientSchema
from app.use_cases.clients.exceptions import ClientProfileNotFoundError

__all__ = ["GetClientProfileUseCase", "get_get_client_profile_use_case"]

logger = get_logger("app.client_profile")


class GetClientProfileUseCase:
    def __init__(self, client_repo: ClientRepository) -> None:
        self._client_repo = client_repo

    async def __call__(self, user_id: UUID) -> ClientSchema:
        with log_context(use_case="get_client_profile", user_id=str(user_id)):
            client = await self._client_repo.primary_client_profile_for_user(user_id)
            if client is None:
                logger.warning("failed", reason="client_profile_not_found")
                raise ClientProfileNotFoundError()

            return ClientSchema.model_validate(client)


def get_get_client_profile_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
) -> GetClientProfileUseCase:
    return GetClientProfileUseCase(client_repo)
