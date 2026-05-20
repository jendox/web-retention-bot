from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends, status

from app.core.structured_logging import get_logger, log_context
from app.models.booking import Booking, BookingStatus
from app.models.master import MasterProfile
from app.models.service import Service
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.repositories.clients import ClientRepository, get_client_repo
from app.repositories.services import ServiceRepository, get_service_repo
from app.repositories.users import UserRepository, get_user_repo
from app.schemas.booking import BookingCreate, BookingOut
from app.schemas.master import MasterProfileSchema
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
    slots_contain,
)
from app.use_cases.booking.exceptions import CreateBookingError

logger = get_logger("app.booking")


def normalize_start_at(start_at: datetime) -> datetime:
    if start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=UTC)
    return start_at.astimezone(UTC)


class CreateBookingUseCase:
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
        if not service or not service.is_active:
            logger.warning("failed", reason="service_not_found_or_inactive", master_id=str(master_id))
            raise CreateBookingError(status_code=status.HTTP_404_NOT_FOUND, error_message="Service not found")
        return service

    async def _ensure_client_link_exists(self, master_id: UUID, client_id: UUID) -> None:
        if not await self._client_repo.link_exists(master_id, client_id):
            logger.warning("failed", reason="unknown_client_linkage", master_id=str(master_id))
            raise CreateBookingError(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_message="Unknown client linkage",
            )

    async def _ensure_slot_available(self, master: MasterProfile, service: Service, start_utc: datetime) -> None:
        master_profile = MasterProfileSchema.model_validate(master)
        booking_day = master_profile.calendar_day_for_master(start_utc)
        slots = await self._available_slots_use_case(
            master_id=master.id,
            service_id=service.id,
            calendar_day=booking_day,
        )
        if not slots_contain([slot.start_at for slot in slots], start_utc):
            logger.warning(
                "failed",
                reason="requested_slot_unavailable",
                master_id=str(master.id),
                start_at=start_utc.isoformat(),
            )
            raise CreateBookingError(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_message="Requested slot unavailable",
            )

    async def _ensure_no_booking_conflict(self, master_id: UUID, start_utc: datetime, end_utc: datetime) -> None:
        if await self._booking_repo.has_conflict(master_id, start_utc, end_utc):
            logger.warning(
                "failed",
                reason="overlapping_booking",
                master_id=str(master_id),
                start_at=start_utc.isoformat(),
                end_at=end_utc.isoformat(),
            )
            raise CreateBookingError(
                status_code=status.HTTP_409_CONFLICT,
                error_message="Overlapping booking exists",
            )

    @staticmethod
    def _build_booking(payload: BookingCreate, master: MasterProfile, service: Service, start_utc: datetime) -> Booking:
        end_utc = start_utc + timedelta(minutes=service.duration_min)
        return Booking(
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

    async def __call__(self, payload: BookingCreate, *, master: MasterProfile) -> BookingOut:
        with log_context(
            use_case="create_booking",
            actor_master_id=str(master.id),
            client_id=str(payload.client_id),
            service_id=str(payload.service_id),
        ):
            service = await self._get_active_service(payload.service_id, master.id)
            await self._ensure_client_link_exists(master.id, payload.client_id)

            start_utc = normalize_start_at(payload.start_at)
            await self._ensure_slot_available(master, service, start_utc)

            booking = self._build_booking(payload, master, service, start_utc)
            await self._ensure_no_booking_conflict(master.id, booking.start_at, booking.end_at)

            created = await self._booking_repo.create(booking)
            logger.info(
                "created",
                booking_id=str(created.id),
                master_id=str(master.id),
                start_at=booking.start_at.isoformat(),
                end_at=booking.end_at.isoformat(),
            )

            client = await self._client_repo.get_client(payload.client_id)
            if client is not None and client.user_id is not None:
                user = await self._user_repo.get_by_id(client.user_id)
                recipient = resolve_booking_client_recipient(client, user)
                if recipient is not None:
                    title, body, link_url = booking_created_in_app_copy(
                        master_display_name=master.display_name,
                        service_name=service.name,
                        start_at=created.start_at,
                        master_timezone=master.timezone,
                    )
                    await self._dispatcher.dispatch_booking_created(
                        booking_id=created.id,
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

            return BookingOut.model_validate(created)


def get_create_booking_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
    available_slots_use_case: Annotated[AvailableSlotsUseCase, Depends(get_available_slots_use_case)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> CreateBookingUseCase:
    return CreateBookingUseCase(
        user_repo,
        client_repo,
        service_repo,
        booking_repo,
        available_slots_use_case,
        dispatcher,
    )
