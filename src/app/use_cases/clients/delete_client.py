from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.repositories.clients import ClientRepository, get_client_repo
from app.use_cases.clients.exceptions import ClientHasBookingsError, ClientHasInvitationError
from app.use_cases.clients.mixins import GetClientMixin

__all__ = ["DeleteClientUseCase", "get_delete_client_use_case"]

logger = get_logger("app.client")


class DeleteClientUseCase(GetClientMixin):
    def __init__(self, client_repo: ClientRepository) -> None:
        self._client_repo = client_repo

    async def __call__(self, *, master_id: UUID, client_id: UUID) -> None:
        with log_context(use_case="delete_client", master_id=str(master_id), client_id=str(client_id)):
            _, client = await self._get_link_with_client(master_id=master_id, client_id=client_id, logger=logger)

            if await self._client_repo.count_bookings_for_client(client_id):
                logger.warning("failed", reason="has_bookings")
                raise ClientHasBookingsError()

            if await self._client_repo.has_invitation_blocking_client(client_id):
                logger.warning("failed", reason="has_invitation")
                raise ClientHasInvitationError()

            await self._client_repo.delete_client(client)
            logger.info("deleted")


def get_delete_client_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
) -> DeleteClientUseCase:
    return DeleteClientUseCase(client_repo)
