from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.booking import Booking, BookingStatus
from app.models.client import Client
from app.models.master import MasterProfile
from app.models.service import Service
from app.repositories.base import BaseRepository
from app.schemas.booking import BookingListScope

__all__ = ["BookingRepository", "get_booking_repo"]


def _scope_clause(scope: BookingListScope, now: datetime):
    if scope == BookingListScope.UPCOMING:
        return and_(Booking.status == BookingStatus.SCHEDULED, Booking.end_at >= now)
    return or_(
        Booking.status != BookingStatus.SCHEDULED,
        Booking.end_at < now,
    )


class BookingRepository(BaseRepository):
    async def create(self, booking: Booking) -> Booking:
        self.session.add(booking)
        await self.session.flush()
        return booking

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
            Booking.status == BookingStatus.SCHEDULED,
            Booking.start_at < end_at,
            Booking.end_at > start_at,
        )
        if exclude_booking_id:
            stmt = stmt.where(Booking.id != exclude_booking_id)
        stmt = stmt.limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_for_master(
        self,
        *,
        master_id: UUID,
        limit: int = 500,
    ) -> list[Booking]:
        stmt = (
            select(Booking)
            .where(Booking.master_id == master_id)
            .order_by(Booking.start_at.asc())
            .limit(limit)
        )
        rows = await self.session.execute(stmt)
        return list(rows.scalars())

    async def count_for_master(
        self,
        *,
        master_id: UUID,
        scope: BookingListScope,
        client_id: UUID | None = None,
    ) -> int:
        now = datetime.now(UTC)
        stmt = select(func.count()).select_from(Booking).where(
            Booking.master_id == master_id,
            _scope_clause(scope, now),
        )
        if client_id is not None:
            stmt = stmt.where(Booking.client_id == client_id)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def list_for_master_page(
        self,
        *,
        master_id: UUID,
        scope: BookingListScope,
        limit: int,
        offset: int,
        client_id: UUID | None = None,
    ) -> list[Booking]:
        now = datetime.now(UTC)
        order = Booking.start_at.asc() if scope == BookingListScope.UPCOMING else Booking.start_at.desc()
        stmt = (
            select(Booking)
            .where(
                Booking.master_id == master_id,
                _scope_clause(scope, now),
            )
            .order_by(order)
            .limit(limit)
            .offset(offset)
        )
        if client_id is not None:
            stmt = stmt.where(Booking.client_id == client_id)
        rows = await self.session.execute(stmt)
        return list(rows.scalars())

    async def complete_past_scheduled(self) -> int:
        now = datetime.now(UTC)
        stmt = (
            update(Booking)
            .where(
                Booking.status == BookingStatus.SCHEDULED,
                Booking.end_at < now,
            )
            .values(status=BookingStatus.COMPLETED, updated_at=now)
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0

    async def get_for_master(self, booking_id: UUID, master_id: UUID) -> Booking | None:
        stmt = (
            select(Booking)
            .where(Booking.id == booking_id, Booking.master_id == master_id)
            .limit(1)
        )
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
            Booking.status == BookingStatus.SCHEDULED,
            Booking.start_at < range_end,
            Booking.end_at > range_start,
        )
        rows = await self.session.execute(stmt)
        return list(rows.scalars())

    async def list_with_details_for_linked_user(self, user_id: UUID) -> list[tuple[Booking, str, str]]:
        stmt = (
            select(Booking, MasterProfile.display_name, Service.name)
            .join(Client, Booking.client_id == Client.id)
            .join(MasterProfile, Booking.master_id == MasterProfile.id)
            .join(Service, Booking.service_id == Service.id)
            .where(Client.user_id == user_id)
            .order_by(Booking.start_at.asc())
            .limit(500)
        )
        rows = await self.session.execute(stmt)
        return [(row[0], row[1], row[2]) for row in rows.all()]


def get_booking_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BookingRepository:
    return BookingRepository(session)
