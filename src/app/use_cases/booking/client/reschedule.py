from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models import Booking
from app.models.user import User
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.repositories.clients import ClientRepository, get_client_repo
from app.repositories.masters import MasterRepository, get_master_repo
from app.repositories.services import ServiceRepository, get_service_repo
from app.repositories.users import UserRepository, get_user_repo
from app.schemas.booking import BookingClientListItem, BookingOut, normalize_booking_comment
from app.schemas.client_master import client_label_for_master, master_label_for_client
from app.services.notifications.booking_master_notify import (
    BookingMasterNotifyContext,
    notify_master_booking_moved,
)
from app.services.notifications.dispatcher import NotificationDispatcher, get_notification_dispatcher
from app.use_cases.booking.available_slots import (
    AvailableSlotsUseCase,
    get_available_slots_use_case,
)
from app.use_cases.booking.client.mixins import ClientBookingMixin
from app.use_cases.booking.client.schemas import ClientBookingUseCaseDeps
from app.use_cases.booking.common import ScheduleBookingContext, schedule_booking

__all__ = ["RescheduleClientBookingUseCase", "get_reschedule_client_booking_use_case"]

logger = get_logger("app.booking")


class RescheduleClientBookingUseCase(ClientBookingMixin):
    def __init__(self, deps: ClientBookingUseCaseDeps) -> None:
        if deps.available_slots_use_case is None:
            raise ValueError("available_slots_use_case is required")
        self._available_slots_use_case = deps.available_slots_use_case
        self._booking_repo = deps.booking_repo
        self._master_repo = deps.master_repo
        self._client_repo = deps.client_repo
        self._service_repo = deps.service_repo
        self._user_repo = deps.user_repo
        self._dispatcher = deps.dispatcher

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
        user: User,
        booking_id: UUID,
        start_at: datetime,
        comment: str | None = None,
    ) -> BookingClientListItem:
        with log_context(use_case="reschedule_client_booking", user_id=str(user.id), booking_id=str(booking_id)):
            booking = await self._get_active_booking(booking_id=booking_id, user_id=user.id, logger=logger)
            master = await self._get_master(master_id=booking.master_id, logger=logger)
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
            logger.info("rescheduled", start_at=start_utc.isoformat())

            link_row = await self._client_repo.get_link_with_client(master.id, booking.client_id)
            link, client = link_row if link_row is not None else (None, None)
            master_label = (
                master_label_for_client(link, master)
                if link is not None
                else master.display_name
            )
            if link is not None and client is not None and start_utc != previous_start_at:
                await notify_master_booking_moved(
                    BookingMasterNotifyContext(
                        dispatcher=self._dispatcher,
                        user_repo=self._user_repo,
                        booking=booking,
                        master=master,
                        service=service,
                        client_display_name=client_label_for_master(link, client),
                    ),
                    previous_start_at=previous_start_at,
                )

            return BookingClientListItem(
                **BookingOut.model_validate(booking).model_dump(),
                master_display_name=master_label,
                service_name=service.name,
            )


def get_reschedule_client_booking_use_case(  # noqa: PLR0913, PLR0917
    master_repo: Annotated[MasterRepository, Depends(get_master_repo)],
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    available_slots_use_case: Annotated[AvailableSlotsUseCase, Depends(get_available_slots_use_case)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> RescheduleClientBookingUseCase:
    return RescheduleClientBookingUseCase(
        ClientBookingUseCaseDeps(
            master_repo,
            client_repo,
            service_repo,
            booking_repo,
            user_repo,
            dispatcher,
            available_slots_use_case,
        ),
    )
