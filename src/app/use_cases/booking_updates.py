from datetime import UTC, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import BookingStatus
from app.repositories.bookings import BookingRepository
from app.repositories.masters import MasterRepository
from app.repositories.services import ServiceRepository
from app.use_cases.list_available_slots import (
    calendar_day_for_master,
    collect_slots_for_service,
    slots_contain,
)


async def cancel_booking(session: AsyncSession, master_id: UUID, booking_id: UUID) -> None:
    repo = BookingRepository(session)
    booking = await repo.get_for_master(booking_id, master_id)
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Booking not found")
    booking.status = BookingStatus.cancelled
    await session.flush()


async def reschedule_booking(
    session: AsyncSession,
    master_id: UUID,
    booking_id: UUID,
    start_at,
    *,
    slot_step_minutes: int,
) -> None:
    masters = MasterRepository(session)
    bookings = BookingRepository(session)
    services = ServiceRepository(session)

    booking = await bookings.get_for_master(booking_id, master_id)
    if not booking or booking.status != BookingStatus.scheduled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Active booking not found")

    master = await masters.get(master_id)
    if not master:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Master profile missing")

    service = await services.get_for_master(booking.service_id, master_id)
    if not service:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Service missing")

    if start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=UTC)
    start_utc = start_at.astimezone(UTC)

    booking_day = calendar_day_for_master(start_utc, master.timezone)
    slots = await collect_slots_for_service(
        session,
        master=master,
        service_id=booking.service_id,
        calendar_day=booking_day,
        slot_step_minutes=slot_step_minutes,
    )
    if not slots_contain(slots, start_utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Requested slot unavailable")

    end_utc = start_utc + timedelta(minutes=booking.duration_min)
    conflicts = await bookings.has_conflict(master_id, start_utc, end_utc, exclude_booking_id=booking.id)
    if conflicts:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Overlapping booking exists")

    booking.start_at = start_utc
    booking.end_at = end_utc
    await session.flush()


__all__ = ["cancel_booking", "reschedule_booking"]
