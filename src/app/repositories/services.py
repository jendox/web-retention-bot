"""Service catalogue persistence."""

from uuid import UUID

from sqlalchemy import select

from app.models.service import Service
from app.repositories.base import BaseRepository


class ServiceRepository(BaseRepository):
    async def list_for_master(self, master_id: UUID) -> list[Service]:
        stmt = (
            select(Service)
            .where(Service.master_id == master_id)
            .order_by(Service.sort_order.asc(), Service.created_at.asc())
        )
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

    async def create(self, service: Service) -> Service:
        self.session.add(service)
        await self.session.flush()
        return service
