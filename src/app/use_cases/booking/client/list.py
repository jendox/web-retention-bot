from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.pagination import Pagination
from app.core.structured_logging import get_logger, log_context
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.schemas.booking import BookingClientListItem, BookingListScope, BookingOut
from app.schemas.pagination import PaginatedResponse

__all__ = ["ListClientBookingsUseCase", "get_list_client_bookings_use_case"]

logger = get_logger("app.booking")


class ListClientBookingsUseCase:
    def __init__(self, booking_repo: BookingRepository) -> None:
        self._booking_repo = booking_repo

    async def __call__(
        self,
        user_id: UUID,
        pagination: Pagination,
        *,
        scope: BookingListScope,
    ) -> PaginatedResponse[BookingClientListItem]:
        with log_context(use_case="list_client_bookings", user_id=str(user_id), scope=scope.value):
            total = await self._booking_repo.count_for_client_user(user_id, scope=scope)
            rows = await self._booking_repo.list_for_client_user_page(
                user_id,
                scope=scope,
                limit=pagination.page_size,
                offset=pagination.offset,
            )
            return PaginatedResponse(
                items=[
                    BookingClientListItem(
                        **BookingOut.model_validate(booking).model_dump(),
                        master_display_name=master_display_name,
                        service_name=service_name,
                    )
                    for booking, master_display_name, service_name in rows
                ],
                total=total,
                page=pagination.page,
                page_size=pagination.page_size,
            )


def get_list_client_bookings_use_case(
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
) -> ListClientBookingsUseCase:
    return ListClientBookingsUseCase(booking_repo)
