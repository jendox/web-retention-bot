from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.booking import Booking
from app.models.service import Service
from app.repositories.base import BaseRepository

__all__ = ["ServiceRepository", "get_service_repo"]


class ServiceRepository(BaseRepository):
    @staticmethod
    def _search_filter(search: str):
        pattern = f"%{search.lower()}%"
        return or_(
            func.lower(Service.name).like(pattern),
            func.lower(Service.description).like(pattern),
        )

    async def list_for_master(self, master_id: UUID) -> list[Service]:
        stmt = (
            select(Service)
            .where(Service.master_id == master_id)
            .order_by(Service.sort_order.asc(), Service.created_at.asc())
        )
        rows = await self.session.execute(stmt)
        return list(rows.scalars())

    async def count_for_master(self, master_id: UUID, *, is_active: bool | None, search: str | None = None) -> int:
        stmt = select(func.count()).select_from(Service).where(Service.master_id == master_id)
        if is_active is not None:
            stmt = stmt.where(Service.is_active == is_active)
        if search:
            stmt = stmt.where(self._search_filter(search))
        count = (await self.session.execute(stmt)).scalar_one()
        return int(count)

    async def list_page_for_master(
        self,
        master_id: UUID,
        *,
        limit: int,
        offset: int,
        is_active: bool | None,
        search: str | None = None,
    ) -> list[Service]:
        stmt = (
            select(Service)
            .where(Service.master_id == master_id)
            .order_by(Service.sort_order.asc(), Service.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        if is_active is not None:
            stmt = stmt.where(Service.is_active == is_active)
        if search:
            stmt = stmt.where(self._search_filter(search))
        rows = await self.session.execute(stmt)
        return list(rows.scalars())

    async def get_for_master(self, service_id: UUID, master_id: UUID) -> Service | None:
        stmt = (
            select(Service)
            .where(Service.id == service_id, Service.master_id == master_id)
            .limit(1)
        )
        rows = await self.session.execute(stmt)
        return rows.scalar_one_or_none()

    async def count_bookings_for_service(self, service_id: UUID) -> int:
        stmt = select(func.count()).select_from(Booking).where(Booking.service_id == service_id)
        count = (await self.session.execute(stmt)).scalar_one()
        return int(count)

    async def create(self, service: Service) -> Service:
        self.session.add(service)
        await self.session.flush()
        return service

    async def delete_entity(self, service: Service) -> None:
        await self.session.delete(service)
        await self.session.flush()


def get_service_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ServiceRepository:
    return ServiceRepository(session)
