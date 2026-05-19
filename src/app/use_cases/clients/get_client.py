from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.repositories.bookings import BookingRepository, get_booking_repo
from app.repositories.clients import ClientRepository, get_client_repo
from app.schemas.client import ClientSchema, ClientWithLinkResponse, MasterClientOut

from .enrich_booking_stats import enrich_clients_with_booking_stats
from .exceptions import ClientNotFoundError


class GetClientUseCase:
    def __init__(self, client_repo: ClientRepository, booking_repo: BookingRepository) -> None:
        self._client_repo = client_repo
        self._booking_repo = booking_repo

    async def __call__(self, master_id: UUID, client_id: UUID) -> ClientWithLinkResponse:
        row = await self._client_repo.get_link_with_client(master_id=master_id, client_id=client_id)
        if row is None:
            raise ClientNotFoundError from None
        link, client = row
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
