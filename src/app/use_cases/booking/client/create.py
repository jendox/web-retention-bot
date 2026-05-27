from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models import Booking, User
from app.models.booking import BookingStatus
from app.schemas.booking import BookingClientListItem, BookingOut, ClientBookingCreate
from app.schemas.client_master import client_label_for_master, master_label_for_client
from app.services.notifications.booking_master_notify import BookingMasterNotifyContext, notify_master_booking_created
from app.services.notifications.booking_reminders import BookingReminderRecipient, schedule_booking_reminders
from app.services.notifications.dispatcher import NotificationDispatcher, get_notification_dispatcher
from app.use_cases.booking.available_slots import AvailableSlotsUseCase, get_available_slots_use_case
from app.use_cases.booking.client.deps import get_client_booking_use_case_repos_deps
from app.use_cases.booking.client.mixins import ClientBookingMixin
from app.use_cases.booking.client.schemas import ClientBookingUseCaseReposDeps
from app.use_cases.booking.common import ScheduleBookingContext, schedule_booking
from app.use_cases.booking.exceptions import (
    BookingNotLinkedToMasterError,
)

__all__ = ["CreateClientBookingUseCase", "get_create_client_booking_use_case"]

logger = get_logger("app.booking")


class CreateClientBookingUseCase(ClientBookingMixin):
    def __init__(
        self,
        repos_deps: ClientBookingUseCaseReposDeps,
        available_slots_use_case: AvailableSlotsUseCase,
        dispatcher: NotificationDispatcher,
    ) -> None:
        self._master_repo = repos_deps.master_repo
        self._user_repo = repos_deps.user_repo
        self._client_repo = repos_deps.client_repo
        self._service_repo = repos_deps.service_repo
        self._booking_repo = repos_deps.booking_repo
        self._scheduled_notifications_repo = repos_deps.scheduled_notifications_repo
        self._available_slots_use_case = available_slots_use_case
        self._dispatcher = dispatcher

    async def __call__(self, payload: ClientBookingCreate, *, user: User) -> BookingClientListItem:
        with log_context(
            use_case="create_client_booking",
            actor_user_id=str(user.id),
            master_id=str(payload.master_id),
            service_id=str(payload.service_id),
        ):
            master = await self._get_master(master_id=payload.master_id, logger=logger)

            link_row = await self._client_repo.get_linked_client_for_master_user(payload.master_id, user.id)
            if link_row is None:
                logger.warning("failed", reason="client_not_linked_to_master")
                raise BookingNotLinkedToMasterError()
            link, client = link_row

            service = await self._get_service(
                service_id=payload.service_id,
                master_id=master.id,
                active_only=True,
                logger=logger,
            )

            start_utc, end_utc = await schedule_booking(
                self._available_slots_use_case,
                self._booking_repo,
                schedule_context=ScheduleBookingContext(
                    master=master,
                    service=service,
                    start_at=payload.start_at,
                    duration_min=service.duration_min,
                ),
                logger=logger,
            )

            booking = Booking(
                master_id=master.id,
                client_id=client.id,
                service_id=service.id,
                start_at=start_utc,
                end_at=end_utc,
                duration_min=service.duration_min,
                price_snapshot=service.price,
                currency_snapshot=str(service.currency),
                status=BookingStatus.SCHEDULED,
            )

            created = await self._booking_repo.create(booking)
            logger.info("created", booking_id=str(created.id))

            await schedule_booking_reminders(
                repo=self._scheduled_notifications_repo,
                booking=created,
                recipient=BookingReminderRecipient(
                    user_id=user.id,
                    client_id=client.id,
                ),
            )

            await notify_master_booking_created(
                BookingMasterNotifyContext(
                    dispatcher=self._dispatcher,
                    user_repo=self._user_repo,
                    booking=created,
                    master=master,
                    service=service,
                    client_display_name=client_label_for_master(link, client),
                ),
            )

            return BookingClientListItem(
                **BookingOut.model_validate(created).model_dump(),
                master_display_name=master_label_for_client(link, master),
                service_name=service.name,
            )


def get_create_client_booking_use_case(
    repos_deps: Annotated[ClientBookingUseCaseReposDeps, Depends(get_client_booking_use_case_repos_deps)],
    available_slots_use_case: Annotated[AvailableSlotsUseCase, Depends(get_available_slots_use_case)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> CreateClientBookingUseCase:
    return CreateClientBookingUseCase(repos_deps, available_slots_use_case, dispatcher)
