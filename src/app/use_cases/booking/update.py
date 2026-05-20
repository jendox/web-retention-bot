from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends, status

from app.core.structured_logging import get_logger, log_context
from app.models.booking import BookingStatus, booking_needs_attendance_confirmation
from app.models.master import MasterProfile
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.repositories.clients import ClientRepository, get_client_repo
from app.repositories.services import ServiceRepository, get_service_repo
from app.repositories.users import UserRepository, get_user_repo
from app.schemas.booking import BookingOut, normalize_booking_comment
from app.schemas.master import MasterProfileSchema
from app.services.notifications.booking_client_notify import (
    BookingClientNotifyContext,
    notify_client_booking_cancelled,
    notify_client_booking_moved,
)
from app.services.notifications.dispatcher import NotificationDispatcher, get_notification_dispatcher
from app.use_cases.booking.available_slots import (
    AvailableSlotsUseCase,
    get_available_slots_use_case,
    slots_contain,
)
from app.use_cases.booking.exceptions import UpdateBookingError

logger = get_logger("app.booking")


def _normalize_start_at(start_at: datetime) -> datetime:
    if start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=UTC)
    return start_at.astimezone(UTC)


class CancelBookingUseCase:
    def __init__(
        self,
        booking_repo: BookingRepository,
        client_repo: ClientRepository,
        service_repo: ServiceRepository,
        user_repo: UserRepository,
        dispatcher: NotificationDispatcher,
    ) -> None:
        self._booking_repo = booking_repo
        self._client_repo = client_repo
        self._service_repo = service_repo
        self._user_repo = user_repo
        self._dispatcher = dispatcher

    async def __call__(self, *, master: MasterProfile, booking_id: UUID, comment: str | None = None) -> None:
        with log_context(use_case="cancel_booking", master_id=str(master.id), booking_id=str(booking_id)):
            booking = await self._booking_repo.get_for_master(booking_id, master.id)
            if not booking:
                logger.warning("failed", reason="booking_not_found")
                raise UpdateBookingError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_message="Booking not found",
                )
            if not booking.status.blocks_calendar:
                logger.warning("failed", reason="booking_not_active")
                raise UpdateBookingError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_message="Active booking not found",
                )

            service = await self._service_repo.get_for_master(booking.service_id, master.id)
            if not service:
                logger.error("failed", reason="service_missing", service_id=str(booking.service_id))
                raise UpdateBookingError(status_code=status.HTTP_404_NOT_FOUND, error_message="Service missing")

            booking.status = BookingStatus.CANCELLED
            booking.cancel_comment = normalize_booking_comment(comment)
            await self._booking_repo.flush()
            logger.info("cancelled")

            await notify_client_booking_cancelled(
                BookingClientNotifyContext(
                    dispatcher=self._dispatcher,
                    user_repo=self._user_repo,
                    client_repo=self._client_repo,
                    booking=booking,
                    master=master,
                    service=service,
                ),
            )


class RescheduleBookingUseCase:
    def __init__(
        self,
        booking_repo: BookingRepository,
        service_repo: ServiceRepository,
        client_repo: ClientRepository,
        user_repo: UserRepository,
        available_slots_use_case: AvailableSlotsUseCase,
        dispatcher: NotificationDispatcher,
    ) -> None:
        self._booking_repo = booking_repo
        self._service_repo = service_repo
        self._client_repo = client_repo
        self._user_repo = user_repo
        self._available_slots_use_case = available_slots_use_case
        self._dispatcher = dispatcher

    async def __call__(
        self,
        *,
        master: MasterProfile,
        booking_id: UUID,
        start_at: datetime,
        comment: str | None = None,
    ) -> BookingOut:
        with log_context(use_case="reschedule_booking", master_id=str(master.id), booking_id=str(booking_id)):
            booking = await self._booking_repo.get_for_master(booking_id, master.id)
            if not booking or not booking.status.blocks_calendar:
                logger.warning("failed", reason="active_booking_not_found")
                raise UpdateBookingError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_message="Active booking not found",
                )

            service = await self._service_repo.get_for_master(booking.service_id, master.id)
            if not service:
                logger.error("failed", reason="service_missing", service_id=str(booking.service_id))
                raise UpdateBookingError(status_code=status.HTTP_404_NOT_FOUND, error_message="Service missing")

            previous_start_at = booking.start_at
            start_utc = _normalize_start_at(start_at)
            master_profile = MasterProfileSchema.model_validate(master)
            booking_day = master_profile.calendar_day_for_master(start_utc)
            slots = await self._available_slots_use_case(
                master_id=master.id,
                service_id=booking.service_id,
                calendar_day=booking_day,
            )
            if not slots_contain([slot.start_at for slot in slots], start_utc):
                logger.warning("failed", reason="requested_slot_unavailable", start_at=start_utc.isoformat())
                raise UpdateBookingError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_message="Requested slot unavailable",
                )

            end_utc = start_utc + timedelta(minutes=booking.duration_min)
            conflicts = await self._booking_repo.has_conflict(
                master.id,
                start_utc,
                end_utc,
                exclude_booking_id=booking.id,
            )
            if conflicts:
                logger.warning(
                    "failed",
                    reason="overlapping_booking",
                    start_at=start_utc.isoformat(),
                    end_at=end_utc.isoformat(),
                )
                raise UpdateBookingError(
                    status_code=status.HTTP_409_CONFLICT,
                    error_message="Overlapping booking exists",
                )

            booking.start_at = start_utc
            booking.end_at = end_utc
            booking.reschedule_comment = normalize_booking_comment(comment)
            await self._booking_repo.flush()
            logger.info("rescheduled", start_at=start_utc.isoformat(), end_at=end_utc.isoformat())

            if start_utc != previous_start_at:
                await notify_client_booking_moved(
                    BookingClientNotifyContext(
                        dispatcher=self._dispatcher,
                        user_repo=self._user_repo,
                        client_repo=self._client_repo,
                        booking=booking,
                        master=master,
                        service=service,
                    ),
                    previous_start_at=previous_start_at,
                )

            return BookingOut.model_validate(booking)


class MarkBookingAttendanceUseCase:
    def __init__(self, booking_repo: BookingRepository) -> None:
        self._booking_repo = booking_repo

    async def __call__(self, *, master_id: UUID, booking_id: UUID, attended: bool) -> BookingOut:
        with log_context(
            use_case="mark_booking_attendance",
            master_id=str(master_id),
            booking_id=str(booking_id),
            attended=attended,
        ):
            booking = await self._booking_repo.get_for_master(booking_id, master_id)
            if not booking:
                logger.warning("failed", reason="booking_not_found")
                raise UpdateBookingError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_message="Booking not found",
                )
            if not booking_needs_attendance_confirmation(booking):
                logger.warning("failed", reason="attendance_not_pending", status=booking.status.value)
                raise UpdateBookingError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_message="Attendance already marked or booking is not awaiting confirmation",
                )
            now = datetime.now(UTC)
            if attended:
                booking.attendance_confirmed_at = now
            else:
                booking.status = BookingStatus.NO_SHOW
                booking.attendance_confirmed_at = now
            await self._booking_repo.flush()
            logger.info("marked", status=booking.status.value)
            return BookingOut.model_validate(booking)


def get_cancel_booking_use_case(
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> CancelBookingUseCase:
    return CancelBookingUseCase(booking_repo, client_repo, service_repo, user_repo, dispatcher)


def get_reschedule_booking_use_case(
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    available_slots_use_case: Annotated[AvailableSlotsUseCase, Depends(get_available_slots_use_case)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> RescheduleBookingUseCase:
    return RescheduleBookingUseCase(
        booking_repo,
        service_repo,
        client_repo,
        user_repo,
        available_slots_use_case,
        dispatcher,
    )


def get_mark_booking_attendance_use_case(
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
) -> MarkBookingAttendanceUseCase:
    return MarkBookingAttendanceUseCase(booking_repo)
