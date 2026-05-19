from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.repositories.bookings import BookingRepository, get_booking_repo
from app.schemas.booking import BookingClientListItem, BookingOut


class ListMasterBookingsUseCase:
    def __init__(self, booking_repo: BookingRepository) -> None:
        self._booking_repo = booking_repo

    async def __call__(self, master_id: UUID) -> list[BookingOut]:
        bookings = await self._booking_repo.list_for_master(master_id)
        return [BookingOut.model_validate(booking) for booking in bookings]


class ListClientBookingsUseCase:
    def __init__(self, booking_repo: BookingRepository) -> None:
        self._booking_repo = booking_repo

    async def __call__(self, user_id: UUID) -> list[BookingClientListItem]:
        rows = await self._booking_repo.list_with_details_for_linked_user(user_id)
        return [
            BookingClientListItem(
                **BookingOut.model_validate(booking).model_dump(),
                master_display_name=master_display_name,
                service_name=service_name,
            )
            for booking, master_display_name, service_name in rows
        ]


def get_list_master_bookings_use_case(
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
) -> ListMasterBookingsUseCase:
    return ListMasterBookingsUseCase(booking_repo)


def get_list_client_bookings_use_case(
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
) -> ListClientBookingsUseCase:
    return ListClientBookingsUseCase(booking_repo)
