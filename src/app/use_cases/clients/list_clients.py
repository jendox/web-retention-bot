from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.pagination import Pagination
from app.core.structured_logging import get_logger, log_context
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.repositories.clients import ClientRepository, get_client_repo
from app.schemas.client import ClientSchema, ClientWithLinkResponse, MasterClientOut
from app.schemas.pagination import PaginatedResponse
from app.use_cases.clients.enrich_booking_stats import enrich_clients_with_booking_stats

__all__ = ["ListClientsUseCase", "get_list_clients_use_case"]

logger = get_logger("app.client")


class ListClientsUseCase:
    def __init__(self, client_repo: ClientRepository, booking_repo: BookingRepository) -> None:
        self._client_repo = client_repo
        self._booking_repo = booking_repo

    async def __call__(
        self,
        master_id: UUID,
        pagination: Pagination,
        *,
        search: str | None = None,
    ) -> PaginatedResponse[ClientWithLinkResponse]:
        with log_context(use_case="list_clients", master_id=str(master_id)):
            normalized_search = search.strip() if search and search.strip() else None
            total = await self._client_repo.count_clients_for_master(master_id, search=normalized_search)
            rows = await self._client_repo.master_clients_with_clients_page(
                master_id,
                limit=pagination.page_size,
                offset=pagination.offset,
                search=normalized_search,
            )
            items = [
                ClientWithLinkResponse(
                    link=MasterClientOut.model_validate(link),
                    client=ClientSchema.model_validate(client),
                )
                for link, client in rows
            ]
            await enrich_clients_with_booking_stats(
                self._booking_repo,
                master_id=master_id,
                items=items,
            )
            return PaginatedResponse(
                items=items,
                total=total,
                page=pagination.page,
                page_size=pagination.page_size,
            )


def get_list_clients_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
) -> ListClientsUseCase:
    return ListClientsUseCase(client_repo, booking_repo)
