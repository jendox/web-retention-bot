from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.repositories.clients import ClientRepository, get_client_repo
from app.schemas.client import ClientSchema, ClientWithLinkResponse, MasterClientOut
from app.use_cases.clients.enrich_booking_stats import enrich_clients_with_booking_stats
from app.use_cases.clients.mixins import GetClientMixin

__all__ = ["GetClientUseCase", "get_get_client_use_case"]

logger = get_logger("app.client")


class GetClientUseCase(GetClientMixin):
    def __init__(self, client_repo: ClientRepository, booking_repo: BookingRepository) -> None:
        self._client_repo = client_repo
        self._booking_repo = booking_repo

    async def __call__(self, master_id: UUID, client_id: UUID) -> ClientWithLinkResponse:
        with log_context(use_case="get_client", master_id=str(master_id), client_id=str(client_id)):
            link, client = await self._get_link_with_client(master_id=master_id, client_id=client_id, logger=logger)
            response = ClientWithLinkResponse(
                client=ClientSchema.model_validate(client),
                link=MasterClientOut.model_validate(link),
            )
            await enrich_clients_with_booking_stats(
                self._booking_repo,
                master_id=master_id,
                items=[response],
            )
            return response


def get_get_client_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
) -> GetClientUseCase:
    return GetClientUseCase(client_repo, booking_repo)
