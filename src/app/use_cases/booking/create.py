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
from app.repositories.invitations import InvitationRepository, get_invitation_repo
from app.repositories.masters import MasterRepository, get_master_repo
from app.repositories.services import ServiceRepository, get_service_repo
from app.schemas.booking import BookingCreate, BookingOut
from app.schemas.master import MasterProfileSchema
from app.use_cases.booking.available_slots import (
    AvailableSlotsUseCase,
    get_available_slots_use_case,
    slots_contain,
)
from app.use_cases.booking.exceptions import CreateBookingError

logger = get_logger("app.booking")


def _normalize_start_at(start_at: datetime) -> datetime:
    if start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=UTC)
    return start_at.astimezone(UTC)


class CreateBookingUseCase:
    def __init__(
        self,
        client_repo: ClientRepository,
        service_repo: ServiceRepository,
        master_repo: MasterRepository,
        invitation_repo: InvitationRepository,
        booking_repo: BookingRepository,
        available_slots_use_case: AvailableSlotsUseCase,
    ) -> None:
        self._client_repo = client_repo
        self._service_repo = service_repo
        self._master_repo = master_repo
        self._invitation_repo = invitation_repo
        self._booking_repo = booking_repo
        self._available_slots_use_case = available_slots_use_case

    async def _resolve_master_id(self, payload: BookingCreate, actor_master_id: UUID | None) -> UUID:
        if actor_master_id is not None:
            return actor_master_id
        if not payload.invite_token:
            logger.warning("failed", reason="authentication_required")
            raise CreateBookingError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_message="Authentication required",
            )

        invitation = await self._invitation_repo.get_by_token(payload.invite_token)
        if not invitation:
            logger.warning("failed", reason="invitation_not_found")
            raise CreateBookingError(status_code=status.HTTP_404_NOT_FOUND, error_message="Invitation not found")
        if invitation.linked_client_id is None or invitation.accepted_at is None:
            logger.warning("failed", reason="invitation_not_accepted", invitation_id=str(invitation.id))
            raise CreateBookingError(
                status_code=status.HTTP_403_FORBIDDEN,
                error_message="Invitation must be accepted first",
            )
        if invitation.linked_client_id != payload.client_id:
            logger.warning(
                "failed",
                reason="client_mismatch_for_invitation",
                invitation_id=str(invitation.id),
                linked_client_id=str(invitation.linked_client_id),
            )
            raise CreateBookingError(
                status_code=status.HTTP_403_FORBIDDEN,
                error_message="Client mismatch for invitation",
            )
        if invitation.expires_at < datetime.now(UTC):
            logger.warning("failed", reason="invitation_expired", invitation_id=str(invitation.id))
            raise CreateBookingError(status_code=status.HTTP_410_GONE, error_message="Invitation expired")
        return invitation.master_id

    async def _get_master(self, master_id: UUID) -> MasterProfile:
        master = await self._master_repo.get_by_master_id(master_id)
        if not master:
            logger.error("failed", reason="master_missing", master_id=str(master_id))
            raise CreateBookingError(status_code=status.HTTP_404_NOT_FOUND, error_message="Master profile missing")
        return master

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
            status=BookingStatus.scheduled,
        )

    async def __call__(self, payload: BookingCreate, *, actor_master_id: UUID | None) -> BookingOut:
        with log_context(
            use_case="create_booking",
            actor_master_id=str(actor_master_id) if actor_master_id else None,
            client_id=str(payload.client_id),
            service_id=str(payload.service_id),
        ):
            master_id = await self._resolve_master_id(payload, actor_master_id)
            master = await self._get_master(master_id)
            service = await self._get_active_service(payload.service_id, master.id)
            await self._ensure_client_link_exists(master.id, payload.client_id)

            start_utc = _normalize_start_at(payload.start_at)
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
            return BookingOut.model_validate(created)


def get_create_booking_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    master_repo: Annotated[MasterRepository, Depends(get_master_repo)],
    invitation_repo: Annotated[InvitationRepository, Depends(get_invitation_repo)],
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
    available_slots_use_case: Annotated[AvailableSlotsUseCase, Depends(get_available_slots_use_case)],
) -> CreateBookingUseCase:
    return CreateBookingUseCase(
        client_repo,
        service_repo,
        master_repo,
        invitation_repo,
        booking_repo,
        available_slots_use_case,
    )
