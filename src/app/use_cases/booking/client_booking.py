from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends, status

from app.core.structured_logging import get_logger, log_context
from app.models.booking import Booking, BookingStatus
from app.models.master import MasterProfile
from app.models.user import User
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.repositories.clients import ClientRepository, get_client_repo
from app.repositories.masters import MasterRepository, get_master_repo
from app.repositories.services import ServiceRepository, get_service_repo
from app.schemas.booking import BookingClientListItem, BookingOut, ClientBookingCreate
from app.schemas.client_master import master_label_for_client
from app.schemas.master import MasterProfileSchema
from app.use_cases.booking.available_slots import (
    AvailableSlotsUseCase,
    get_available_slots_use_case,
    slots_contain,
)
from app.use_cases.booking.create import normalize_start_at
from app.use_cases.booking.exceptions import CreateBookingError, UpdateBookingError

logger = get_logger("app.booking.client")


class CreateClientBookingUseCase:
    def __init__(
        self,
        master_repo: MasterRepository,
        client_repo: ClientRepository,
        service_repo: ServiceRepository,
        booking_repo: BookingRepository,
        available_slots_use_case: AvailableSlotsUseCase,
    ) -> None:
        self._master_repo = master_repo
        self._client_repo = client_repo
        self._service_repo = service_repo
        self._booking_repo = booking_repo
        self._available_slots_use_case = available_slots_use_case

    async def __call__(self, payload: ClientBookingCreate, *, user: User) -> BookingClientListItem:
        with log_context(
            use_case="create_client_booking",
            actor_user_id=str(user.id),
            master_id=str(payload.master_id),
            service_id=str(payload.service_id),
        ):
            master = await self._master_repo.get_by_master_id(payload.master_id)
            if master is None:
                raise CreateBookingError(status_code=status.HTTP_404_NOT_FOUND, error_message="Master not found")

            link_row = await self._client_repo.get_linked_client_for_master_user(payload.master_id, user.id)
            if link_row is None:
                raise CreateBookingError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_message="Not linked to this master",
                )
            link, client = link_row

            service = await self._service_repo.get_for_master(payload.service_id, master.id)
            if not service or not service.is_active:
                raise CreateBookingError(status_code=status.HTTP_404_NOT_FOUND, error_message="Service not found")

            start_utc = normalize_start_at(payload.start_at)
            await self._ensure_slot_available(master, service.id, start_utc)

            end_utc = start_utc + timedelta(minutes=service.duration_min)
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
            if await self._booking_repo.has_conflict(master.id, booking.start_at, booking.end_at):
                raise CreateBookingError(
                    status_code=status.HTTP_409_CONFLICT,
                    error_message="Overlapping booking exists",
                )

            created = await self._booking_repo.create(booking)
            logger.info("created", booking_id=str(created.id))
            return BookingClientListItem(
                **BookingOut.model_validate(created).model_dump(),
                master_display_name=master_label_for_client(link, master),
                service_name=service.name,
            )

    async def _ensure_slot_available(
        self,
        master: MasterProfile,
        service_id: UUID,
        start_utc: datetime,
    ) -> None:
        master_profile = MasterProfileSchema.model_validate(master)
        booking_day = master_profile.calendar_day_for_master(start_utc)
        slots = await self._available_slots_use_case(
            master_id=master.id,
            service_id=service_id,
            calendar_day=booking_day,
        )
        if not slots_contain([slot.start_at for slot in slots], start_utc):
            raise CreateBookingError(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_message="Requested slot unavailable",
            )


class CancelClientBookingUseCase:
    def __init__(self, booking_repo: BookingRepository) -> None:
        self._booking_repo = booking_repo

    async def __call__(self, *, user: User, booking_id: UUID) -> None:
        with log_context(use_case="cancel_client_booking", user_id=str(user.id), booking_id=str(booking_id)):
            booking = await self._booking_repo.get_for_user(booking_id, user.id)
            if not booking or not booking.status.blocks_calendar:
                raise UpdateBookingError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_message="Active booking not found",
                )
            booking.status = BookingStatus.CANCELLED
            await self._booking_repo.flush()
            logger.info("cancelled")


class RescheduleClientBookingUseCase:
    def __init__(
        self,
        master_repo: MasterRepository,
        client_repo: ClientRepository,
        booking_repo: BookingRepository,
        service_repo: ServiceRepository,
        available_slots_use_case: AvailableSlotsUseCase,
    ) -> None:
        self._master_repo = master_repo
        self._client_repo = client_repo
        self._booking_repo = booking_repo
        self._service_repo = service_repo
        self._available_slots_use_case = available_slots_use_case

    async def __call__(self, *, user: User, booking_id: UUID, start_at: datetime) -> BookingClientListItem:
        with log_context(use_case="reschedule_client_booking", user_id=str(user.id), booking_id=str(booking_id)):
            booking = await self._booking_repo.get_for_user(booking_id, user.id)
            if not booking or not booking.status.blocks_calendar:
                raise UpdateBookingError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_message="Active booking not found",
                )

            master = await self._master_repo.get_by_master_id(booking.master_id)
            if master is None:
                raise UpdateBookingError(status_code=status.HTTP_404_NOT_FOUND, error_message="Master not found")

            service = await self._service_repo.get_for_master(booking.service_id, master.id)
            if not service:
                raise UpdateBookingError(status_code=status.HTTP_404_NOT_FOUND, error_message="Service missing")

            start_utc = normalize_start_at(start_at)
            master_profile = MasterProfileSchema.model_validate(master)
            booking_day = master_profile.calendar_day_for_master(start_utc)
            slots = await self._available_slots_use_case(
                master_id=master.id,
                service_id=booking.service_id,
                calendar_day=booking_day,
            )
            if not slots_contain([slot.start_at for slot in slots], start_utc):
                raise UpdateBookingError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_message="Requested slot unavailable",
                )

            end_utc = start_utc + timedelta(minutes=booking.duration_min)
            if await self._booking_repo.has_conflict(
                master.id,
                start_utc,
                end_utc,
                exclude_booking_id=booking.id,
            ):
                raise UpdateBookingError(
                    status_code=status.HTTP_409_CONFLICT,
                    error_message="Overlapping booking exists",
                )

            booking.start_at = start_utc
            booking.end_at = end_utc
            await self._booking_repo.flush()
            logger.info("rescheduled", start_at=start_utc.isoformat())

            link_row = await self._client_repo.get_link_with_client(master.id, booking.client_id)
            master_label = (
                master_label_for_client(link_row[0], master)
                if link_row is not None
                else master.display_name
            )
            return BookingClientListItem(
                **BookingOut.model_validate(booking).model_dump(),
                master_display_name=master_label,
                service_name=service.name,
            )


def get_create_client_booking_use_case(
    master_repo: Annotated[MasterRepository, Depends(get_master_repo)],
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
    available_slots_use_case: Annotated[AvailableSlotsUseCase, Depends(get_available_slots_use_case)],
) -> CreateClientBookingUseCase:
    return CreateClientBookingUseCase(
        master_repo,
        client_repo,
        service_repo,
        booking_repo,
        available_slots_use_case,
    )


def get_cancel_client_booking_use_case(
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
) -> CancelClientBookingUseCase:
    return CancelClientBookingUseCase(booking_repo)


def get_reschedule_client_booking_use_case(
    master_repo: Annotated[MasterRepository, Depends(get_master_repo)],
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    available_slots_use_case: Annotated[AvailableSlotsUseCase, Depends(get_available_slots_use_case)],
) -> RescheduleClientBookingUseCase:
    return RescheduleClientBookingUseCase(
        master_repo,
        client_repo,
        booking_repo,
        service_repo,
        available_slots_use_case,
    )
