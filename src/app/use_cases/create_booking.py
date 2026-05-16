from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.structured_logging import get_logger, log_context
from app.models.booking import Booking, BookingStatus
from app.repositories.bookings import BookingRepository
from app.repositories.clients import ClientRepository
from app.repositories.invitations import InvitationRepository
from app.repositories.masters import MasterRepository
from app.repositories.services import ServiceRepository
from app.schemas.booking import BookingCreate
from app.use_cases.list_available_slots import (
    calendar_day_for_master,
    collect_slots_for_service,
    slots_contain,
)

logger = get_logger("app.booking")


async def create_booking(
    session: AsyncSession,
    payload: BookingCreate,
    *,
    actor_master_id: UUID | None,
    slot_step_minutes: int,
) -> Booking:
    clients = ClientRepository(session)
    services = ServiceRepository(session)
    masters = MasterRepository(session)
    invites = InvitationRepository(session)
    bookings = BookingRepository(session)

    with log_context(
        use_case="create_booking",
        actor_master_id=str(actor_master_id) if actor_master_id else None,
        client_id=str(payload.client_id),
        service_id=str(payload.service_id),
    ):
        master_uuid: UUID
        if actor_master_id is not None:
            master_uuid = actor_master_id
        elif payload.invite_token:
            invitation = await invites.get_by_token(payload.invite_token)
            if not invitation:
                logger.warning("failed", reason="invitation_not_found")
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invitation not found")
            if invitation.linked_client_id is None or invitation.accepted_at is None:
                logger.warning("failed", reason="invitation_not_accepted", invitation_id=str(invitation.id))
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Invitation must be accepted first")
            if invitation.linked_client_id != payload.client_id:
                logger.warning(
                    "failed",
                    reason="client_mismatch_for_invitation",
                    invitation_id=str(invitation.id),
                    linked_client_id=str(invitation.linked_client_id),
                )
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Client mismatch for invitation")
            if invitation.expires_at < datetime.now(UTC):
                logger.warning("failed", reason="invitation_expired", invitation_id=str(invitation.id))
                raise HTTPException(status.HTTP_410_GONE, detail="Invitation expired")
            master_uuid = invitation.master_id
        else:
            logger.warning("failed", reason="authentication_required")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

        master = await masters.get(master_uuid)
        if not master:
            logger.error("failed", reason="master_missing", master_id=str(master_uuid))
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Master profile missing")

        service = await services.get_for_master(payload.service_id, master.id)
        if not service or not service.is_active:
            logger.warning("failed", reason="service_not_found_or_inactive", master_id=str(master.id))
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Service not found")

        if not await clients.link_exists(master.id, payload.client_id):
            logger.warning("failed", reason="unknown_client_linkage", master_id=str(master.id))
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown client linkage")

        start_at = payload.start_at
        if start_at.tzinfo is None:
            start_at = start_at.replace(tzinfo=UTC)
        start_utc = start_at.astimezone(UTC)

        booking_day = calendar_day_for_master(start_utc, master.timezone)
        slots = await collect_slots_for_service(
            session,
            master=master,
            service_id=service.id,
            calendar_day=booking_day,
            slot_step_minutes=slot_step_minutes,
        )
        if not slots_contain(slots, start_utc):
            logger.warning(
                "failed",
                reason="requested_slot_unavailable",
                master_id=str(master.id),
                start_at=start_utc.isoformat(),
            )
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Requested slot unavailable")

        end_utc = start_utc + timedelta(minutes=service.duration_min)

        if await bookings.has_conflict(master.id, start_utc, end_utc):
            logger.warning(
                "failed",
                reason="overlapping_booking",
                master_id=str(master.id),
                start_at=start_utc.isoformat(),
                end_at=end_utc.isoformat(),
            )
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Overlapping booking exists")

        booking = Booking(
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
        created = await bookings.add(booking)
        logger.info(
            "created",
            booking_id=str(created.id),
            master_id=str(master.id),
            start_at=start_utc.isoformat(),
            end_at=end_utc.isoformat(),
        )
        return created


__all__ = ["create_booking"]
