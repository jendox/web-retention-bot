from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models.booking import Booking, BookingStatus
from app.models.master import MasterProfile
from app.models.service import Service
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.repositories.clients import ClientRepository, get_client_repo
from app.repositories.services import ServiceRepository, get_service_repo
from app.repositories.users import UserRepository, get_user_repo
from app.schemas.booking import BookingCreate, BookingOut
from app.services.notifications.dispatcher import (
    BookingEmailContext,
    NotificationDispatcher,
    get_notification_dispatcher,
)
from app.services.notifications.mail_render import BOOKING_EMAIL_AUDIENCE_CLIENT, booking_created_in_app_copy
from app.services.notifications.recipients import resolve_booking_client_recipient
from app.use_cases.booking.available_slots import (
    AvailableSlotsUseCase,
    get_available_slots_use_case,
)
from app.use_cases.booking.common import ScheduleBookingContext, schedule_booking
from app.use_cases.booking.exceptions import (
    BookingServiceNotFoundError,
    BookingUnknownClientLinkageError,
)

__all__ = ["CreateMasterBookingUseCase", "get_create_master_booking_use_case"]

logger = get_logger("app.booking")


class CreateMasterBookingUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        client_repo: ClientRepository,
        service_repo: ServiceRepository,
        booking_repo: BookingRepository,
        available_slots_use_case: AvailableSlotsUseCase,
        dispatcher: NotificationDispatcher,
    ) -> None:
        self._user_repo = user_repo
        self._client_repo = client_repo
        self._service_repo = service_repo
        self._booking_repo = booking_repo
        self._available_slots_use_case = available_slots_use_case
        self._dispatcher = dispatcher

    async def _get_active_service(self, service_id: UUID, master_id: UUID) -> Service:
        service = await self._service_repo.get_for_master(service_id, master_id)
        if not service:
            logger.warning("failed", reason="service_not_found")
            raise BookingServiceNotFoundError()

        if not service.is_active:
            logger.warning("failed", reason="service_inactive")
            raise BookingServiceNotFoundError()

        return service

    async def _ensure_client_link_exists(self, master_id: UUID, client_id: UUID) -> None:
        if not await self._client_repo.link_exists(master_id, client_id):
            logger.warning("failed", reason="unknown_client_linkage")
            raise BookingUnknownClientLinkageError()

    async def _notify_recipients(
        self,
        *,
        client_id: UUID,
        master: MasterProfile,
        service_name: str,
        booking_id: UUID,
        booking_start_at: datetime,
    ) -> None:
        client = await self._client_repo.get_client(client_id)
        if client is not None and client.user_id is not None:
            user = await self._user_repo.get_by_id(client.user_id)
            recipient = resolve_booking_client_recipient(client, user)
            if recipient is not None:
                title, body, link_url = booking_created_in_app_copy(
                    master_display_name=master.display_name,
                    service_name=service_name,
                    start_at=booking_start_at,
                    master_timezone=master.timezone,
                )
                await self._dispatcher.dispatch_booking_created(
                    booking_id=booking_id,
                    master_profile_id=master.id,
                    client_id=client.id,
                    recipient=recipient,
                    email_ctx=BookingEmailContext(
                        title=title,
                        body=body,
                        link_url=link_url,
                        payload={"audience": BOOKING_EMAIL_AUDIENCE_CLIENT},
                    ),
                )

    async def __call__(self, payload: BookingCreate, *, master: MasterProfile) -> BookingOut:
        with log_context(
            use_case="create_master_booking",
            master_id=str(master.id),
            client_id=str(payload.client_id),
            service_id=str(payload.service_id),
        ):
            service = await self._get_active_service(payload.service_id, master.id)
            await self._ensure_client_link_exists(master.id, payload.client_id)

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
                client_id=payload.client_id,
                service_id=service.id,
                start_at=start_utc,
                end_at=end_utc,
                duration_min=service.duration_min,
                price_snapshot=service.price,
                currency_snapshot=str(service.currency),
                status=BookingStatus.SCHEDULED,
            )

            created = await self._booking_repo.create(booking)
            logger.info(
                "created",
                booking_id=str(created.id),
                start_at=booking.start_at.isoformat(),
                end_at=booking.end_at.isoformat(),
            )

            await self._notify_recipients(
                client_id=payload.client_id,
                master=master,
                service_name=service.name,
                booking_id=created.id,
                booking_start_at=created.start_at,
            )

            return BookingOut.model_validate(created)


def get_create_master_booking_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
    available_slots_use_case: Annotated[AvailableSlotsUseCase, Depends(get_available_slots_use_case)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> CreateMasterBookingUseCase:
    return CreateMasterBookingUseCase(
        user_repo,
        client_repo,
        service_repo,
        booking_repo,
        available_slots_use_case,
        dispatcher,
    )
