from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models import Booking, User
from app.models.booking import BookingStatus
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.repositories.clients import ClientRepository, get_client_repo
from app.repositories.masters import MasterRepository, get_master_repo
from app.repositories.services import ServiceRepository, get_service_repo
from app.repositories.users import UserRepository, get_user_repo
from app.schemas.booking import BookingClientListItem, BookingOut, ClientBookingCreate
from app.schemas.client_master import client_label_for_master, master_label_for_client
from app.services.notifications.booking_master_notify import BookingMasterNotifyContext, notify_master_booking_created
from app.services.notifications.dispatcher import NotificationDispatcher, get_notification_dispatcher
from app.use_cases.booking.available_slots import AvailableSlotsUseCase, get_available_slots_use_case
from app.use_cases.booking.client.mixins import ClientBookingMixin
from app.use_cases.booking.client.schemas import ClientBookingUseCaseDeps
from app.use_cases.booking.common import ScheduleBookingContext, schedule_booking
from app.use_cases.booking.exceptions import (
    BookingNotLinkedToMasterError,
)

__all__ = ["CreateClientBookingUseCase", "get_create_client_booking_use_case"]

logger = get_logger("app.booking")


class CreateClientBookingUseCase(ClientBookingMixin):
    def __init__(self, deps: ClientBookingUseCaseDeps) -> None:
        if deps.available_slots_use_case is None:
            raise ValueError("Available slots use case required")

        self._master_repo = deps.master_repo
        self._client_repo = deps.client_repo
        self._service_repo = deps.service_repo
        self._booking_repo = deps.booking_repo
        self._user_repo = deps.user_repo
        self._available_slots_use_case = deps.available_slots_use_case
        self._dispatcher = deps.dispatcher

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


def get_create_client_booking_use_case(  # noqa: PLR0913, PLR0917
    master_repo: Annotated[MasterRepository, Depends(get_master_repo)],
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
    available_slots_use_case: Annotated[AvailableSlotsUseCase, Depends(get_available_slots_use_case)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> CreateClientBookingUseCase:
    return CreateClientBookingUseCase(
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
