from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models import Booking
from app.models.booking import BookingStatus, booking_needs_attendance_confirmation
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.schemas.booking import BookingOut
from app.use_cases.booking.exceptions import BookingAttendanceNotPendingError, BookingNotFoundError
from app.use_cases.booking.master.mixins import MasterBookingMixin

__all__ = ["MarkMasterBookingAttendanceUseCase", "get_mark_master_booking_attendance_use_case"]

logger = get_logger("app.booking")


class MarkMasterBookingAttendanceUseCase(MasterBookingMixin):
    def __init__(self, booking_repo: BookingRepository) -> None:
        self._booking_repo = booking_repo

    async def _update_booking(
        self,
        *,
        booking: Booking,
        attended: bool,
    ) -> None:
        now = datetime.now(UTC)
        if attended:
            booking.attendance_confirmed_at = now
        else:
            booking.status = BookingStatus.NO_SHOW
            booking.attendance_confirmed_at = now
        await self._booking_repo.flush()

    async def __call__(self, *, master_id: UUID, booking_id: UUID, attended: bool) -> BookingOut:
        with log_context(
            use_case="mark_master_booking_attendance",
            master_id=str(master_id),
            booking_id=str(booking_id),
            attended=attended,
        ):
            booking = await self._booking_repo.get_for_master(booking_id, master_id)
            if not booking:
                logger.warning("failed", reason="booking_not_found")
                raise BookingNotFoundError()

            if not booking_needs_attendance_confirmation(booking):
                logger.warning("failed", reason="attendance_not_pending", status=booking.status.value)
                raise BookingAttendanceNotPendingError()

            await self._update_booking(booking=booking, attended=attended)
            logger.info("marked", status=booking.status.value)
            return BookingOut.model_validate(booking)


def get_mark_master_booking_attendance_use_case(
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
) -> MarkMasterBookingAttendanceUseCase:
    return MarkMasterBookingAttendanceUseCase(booking_repo)
