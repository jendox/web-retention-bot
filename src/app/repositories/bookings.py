"""Booking queries."""

from uuid import UUID

from sqlalchemy import select

from app.models.booking import Booking, BookingStatus
from app.repositories.base import BaseRepository


class BookingRepository(BaseRepository):
    async def has_conflict(
        self,
        master_id: UUID,
        start_at,
        end_at,
        *,
        exclude_booking_id: UUID | None = None,
    ) -> bool:
        stmt = select(Booking.id).where(
            Booking.master_id == master_id,
            Booking.status == BookingStatus.scheduled,
            Booking.start_at < end_at,
            Booking.end_at > start_at,
        )
        if exclude_booking_id:
            stmt = stmt.where(Booking.id != exclude_booking_id)
        stmt = stmt.limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_for_master(self, master_id: UUID) -> list[Booking]:
        stmt = (
            select(Booking)
            .where(Booking.master_id == master_id)
            .order_by(Booking.start_at.asc())
            .limit(500)
        )
        rows = await self.session.execute(stmt)
        return list(rows.scalars())

    async def get_for_master(self, booking_id: UUID, master_id: UUID) -> Booking | None:
        stmt = select(Booking).where(Booking.id == booking_id, Booking.master_id == master_id).limit(1)
        rows = await self.session.execute(stmt)
        return rows.scalar_one_or_none()

    async def active_between(
        self,
        master_id: UUID,
        range_start,
        range_end,
    ) -> list[Booking]:
        stmt = select(Booking).where(
            Booking.master_id == master_id,
            Booking.status == BookingStatus.scheduled,
            Booking.start_at < range_end,
            Booking.end_at > range_start,
        )
        rows = await self.session.execute(stmt)
        return list(rows.scalars())

    async def add(self, booking: Booking) -> Booking:
        self.session.add(booking)
        await self.session.flush()
        return booking
