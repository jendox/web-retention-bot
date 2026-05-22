from __future__ import annotations

from uuid import UUID

from structlog import BoundLogger

from app.models import Client, MasterClient
from app.use_cases.clients.exceptions import ClientNotFoundError

__all__ = ["GetClientMixin"]


class GetClientMixin:
    async def _get_link_with_client(
        self,
        *,
        master_id: UUID,
        client_id: UUID,
        logger: BoundLogger,
    ) -> tuple[MasterClient, Client]:
        row = await self._client_repo.get_link_with_client(master_id=master_id, client_id=client_id)
        if row is None:
            logger.warning("failed", reason="client_not_found")
            raise ClientNotFoundError()

        link, client = row
        return link, client
