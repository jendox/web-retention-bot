from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.booking import Booking, BookingStatus
from app.models.client import Client, MasterClient
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

    async def get(self, booking_id: UUID) -> Booking | None:
        return await self.session.get(Booking, booking_id)

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
        service_id: UUID | None = None,
    ) -> int:
        now = datetime.now(UTC)
        stmt = select(func.count()).select_from(Booking).where(
            Booking.master_id == master_id,
            _scope_clause(scope, now),
        )
        if client_id is not None:
            stmt = stmt.where(Booking.client_id == client_id)
        if service_id is not None:
            stmt = stmt.where(Booking.service_id == service_id)
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
        service_id: UUID | None = None,
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
        if service_id is not None:
            stmt = stmt.where(Booking.service_id == service_id)
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

    async def get_for_user(self, booking_id: UUID, user_id: UUID) -> Booking | None:
        stmt = (
            select(Booking)
            .join(Client, Booking.client_id == Client.id)
            .where(Booking.id == booking_id, Client.user_id == user_id)
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

    async def no_show_counts_by_client_ids(
        self,
        *,
        master_id: UUID,
        client_ids: list[UUID],
    ) -> dict[UUID, int]:
        if not client_ids:
            return {}
        stmt = (
            select(Booking.client_id, func.count())
            .where(
                Booking.master_id == master_id,
                Booking.client_id.in_(client_ids),
                Booking.status == BookingStatus.NO_SHOW,
            )
            .group_by(Booking.client_id)
        )
        rows = await self.session.execute(stmt)
        return {client_id: int(count) for client_id, count in rows.all()}

    async def sum_completed_revenue_between(
        self,
        *,
        master_id: UUID,
        range_start: datetime,
        range_end: datetime,
    ) -> tuple[Decimal, int]:
        filters = (
            Booking.master_id == master_id,
            Booking.status == BookingStatus.COMPLETED,
            Booking.start_at >= range_start,
            Booking.start_at < range_end,
        )
        stmt = select(
            func.coalesce(func.sum(Booking.price_snapshot), 0),
            func.count(),
        ).where(*filters)
        result = await self.session.execute(stmt)
        amount, count = result.one()
        return Decimal(amount), int(count)

    async def completed_counts_by_client_ids(
        self,
        *,
        master_id: UUID,
        client_ids: list[UUID],
    ) -> dict[UUID, int]:
        if not client_ids:
            return {}
        stmt = (
            select(Booking.client_id, func.count())
            .where(
                Booking.master_id == master_id,
                Booking.client_id.in_(client_ids),
                Booking.status == BookingStatus.COMPLETED,
            )
            .group_by(Booking.client_id)
        )
        rows = await self.session.execute(stmt)
        return {client_id: int(count) for client_id, count in rows.all()}

    def _client_bookings_base(self, user_id: UUID):
        master_display_name = func.coalesce(MasterClient.client_alias, MasterProfile.display_name)
        return (
            select(Booking, master_display_name, Service.name)
            .join(Client, Booking.client_id == Client.id)
            .join(MasterProfile, Booking.master_id == MasterProfile.id)
            .join(
                MasterClient,
                and_(
                    MasterClient.master_id == Booking.master_id,
                    MasterClient.client_id == Booking.client_id,
                ),
            )
            .join(Service, Booking.service_id == Service.id)
            .where(Client.user_id == user_id)
        )

    async def count_for_client_user(self, user_id: UUID, *, scope: BookingListScope) -> int:
        now = datetime.now(UTC)
        stmt = (
            select(func.count())
            .select_from(Booking)
            .join(Client, Booking.client_id == Client.id)
            .where(Client.user_id == user_id, _scope_clause(scope, now))
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def list_for_client_user_page(
        self,
        user_id: UUID,
        *,
        scope: BookingListScope,
        limit: int,
        offset: int,
    ) -> list[tuple[Booking, str, str]]:
        now = datetime.now(UTC)
        order = Booking.start_at.asc() if scope == BookingListScope.UPCOMING else Booking.start_at.desc()
        stmt = (
            self._client_bookings_base(user_id)
            .where(_scope_clause(scope, now))
            .order_by(order)
            .limit(limit)
            .offset(offset)
        )
        rows = await self.session.execute(stmt)
        return [(row[0], row[1], row[2]) for row in rows.all()]


def get_booking_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BookingRepository:
    return BookingRepository(session)
