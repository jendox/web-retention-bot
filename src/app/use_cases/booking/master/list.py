from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.pagination import Pagination
from app.core.structured_logging import get_logger, log_context
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.schemas.booking import BookingListScope, BookingOut
from app.schemas.pagination import PaginatedResponse

__all__ = [
    "ListMasterBookingsUseCase",
    "get_list_master_bookings_use_case",
]

logger = get_logger("app.booking")


class ListMasterBookingsUseCase:
    def __init__(self, booking_repo: BookingRepository) -> None:
        self._booking_repo = booking_repo

    async def __call__(
        self,
        master_id: UUID,
        pagination: Pagination,
        *,
        scope: BookingListScope,
        client_id: UUID | None = None,
        service_id: UUID | None = None,
    ) -> PaginatedResponse[BookingOut]:
        with log_context(use_case="list_master_bookings", master_id=str(master_id), scope=scope.value):
            total = await self._booking_repo.count_for_master(
                master_id=master_id,
                scope=scope,
                client_id=client_id,
                service_id=service_id,
            )
            bookings = await self._booking_repo.list_for_master_page(
                master_id=master_id,
                scope=scope,
                limit=pagination.page_size,
                offset=pagination.offset,
                client_id=client_id,
                service_id=service_id,
            )
            return PaginatedResponse(
                items=[BookingOut.model_validate(booking) for booking in bookings],
                total=total,
                page=pagination.page,
                page_size=pagination.page_size,
            )


def get_list_master_bookings_use_case(
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
) -> ListMasterBookingsUseCase:
    return ListMasterBookingsUseCase(booking_repo)
