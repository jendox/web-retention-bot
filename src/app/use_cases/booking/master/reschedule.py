from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models import Booking, MasterProfile
from app.schemas.booking import BookingOut, normalize_booking_comment
from app.services.notifications.booking_client_notify import BookingClientNotifyContext, notify_client_booking_moved
from app.services.notifications.booking_reminders import (
    reschedule_booking_reminders,
)
from app.services.notifications.dispatcher import NotificationDispatcher, get_notification_dispatcher
from app.use_cases.booking.available_slots import AvailableSlotsUseCase, get_available_slots_use_case
from app.use_cases.booking.common import ScheduleBookingContext, schedule_booking
from app.use_cases.booking.master.deps import get_master_booking_use_case_repos_deps
from app.use_cases.booking.master.mixins import MasterBookingMixin
from app.use_cases.booking.master.schemas import MasterBookingUseCaseReposDeps

__all__ = ["RescheduleMasterBookingUseCase", "get_reschedule_master_booking_use_case"]

logger = get_logger("app.booking")


class RescheduleMasterBookingUseCase(MasterBookingMixin):
    def __init__(
        self,
        repos_deps: MasterBookingUseCaseReposDeps,
        available_slots_use_case: AvailableSlotsUseCase,
        dispatcher: NotificationDispatcher,
    ) -> None:
        self._user_repo = repos_deps.user_repo
        self._client_repo = repos_deps.client_repo
        self._service_repo = repos_deps.service_repo
        self._booking_repo = repos_deps.booking_repo
        self._scheduled_notifications_repo = repos_deps.scheduled_notifications_repo
        self._available_slots_use_case = available_slots_use_case
        self._dispatcher = dispatcher

    async def _update_booking(
        self,
        *,
        booking: Booking,
        start_utc: datetime,
        end_utc: datetime,
        comment: str | None,
    ) -> None:
        booking.start_at = start_utc
        booking.end_at = end_utc
        booking.reschedule_comment = normalize_booking_comment(comment)
        await self._booking_repo.flush()

    async def __call__(
        self,
        *,
        master: MasterProfile,
        booking_id: UUID,
        start_at: datetime,
        comment: str | None = None,
    ) -> BookingOut:
        with log_context(
            use_case="reschedule_master_booking",
            master_id=str(master.id),
            booking_id=str(booking_id),
        ):
            booking = await self._get_active_booking(booking_id=booking_id, master_id=master.id, logger=logger)
            service = await self._get_service(service_id=booking.service_id, master_id=master.id, logger=logger)

            previous_start_at = booking.start_at

            start_utc, end_utc = await schedule_booking(
                self._available_slots_use_case,
                self._booking_repo,
                schedule_context=ScheduleBookingContext(
                    master=master,
                    service=service,
                    start_at=start_at,
                    duration_min=booking.duration_min,
                    booking_id=booking.id,
                ),
                logger=logger,
            )

            await self._update_booking(
                booking=booking,
                start_utc=start_utc,
                end_utc=end_utc,
                comment=comment,
            )

            logger.info("rescheduled", start_at=start_utc.isoformat(), end_at=end_utc.isoformat())

            if start_utc != previous_start_at:
                error = await reschedule_booking_reminders(
                    client_repo=self._client_repo,
                    scheduled_notification_repo=self._scheduled_notifications_repo,
                    booking=booking,
                )
                if error is not None:
                    logger.warning(
                        "reschedule_notification_reminders_failed",
                        reason=error,
                    )

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


def get_reschedule_master_booking_use_case(
    repos_deps: Annotated[MasterBookingUseCaseReposDeps, Depends(get_master_booking_use_case_repos_deps)],
    available_slots_use_case: Annotated[AvailableSlotsUseCase, Depends(get_available_slots_use_case)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> RescheduleMasterBookingUseCase:
    return RescheduleMasterBookingUseCase(repos_deps, available_slots_use_case, dispatcher)
