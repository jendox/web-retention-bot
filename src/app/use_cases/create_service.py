from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import Service
from app.repositories.services import ServiceRepository
from app.schemas.service import ServiceCreate, ServiceUpdate


async def create_service(session: AsyncSession, master_id: UUID, payload: ServiceCreate) -> Service:
    repo = ServiceRepository(session)
    service = Service(
        master_id=master_id,
        name=payload.name,
        description=payload.description,
        duration_min=payload.duration_min,
        price=payload.price,
        currency=payload.currency.upper(),
        is_active=payload.is_active,
        sort_order=payload.sort_order,
    )
    return await repo.create(service)


async def update_service(
    session: AsyncSession,
    master_id: UUID,
    service_id: UUID,
    payload: ServiceUpdate,
) -> Service:
    repo = ServiceRepository(session)
    service = await repo.get_for_master(service_id, master_id)
    if not service:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Service not found")
    if payload.name is not None:
        service.name = payload.name
    if payload.description is not None:
        service.description = payload.description
    if payload.duration_min is not None:
        service.duration_min = payload.duration_min
    if payload.price is not None:
        service.price = payload.price
    if payload.currency is not None:
        service.currency = payload.currency.upper()
    if payload.is_active is not None:
        service.is_active = payload.is_active
    if payload.sort_order is not None:
        service.sort_order = payload.sort_order
    await session.flush()
    return service


async def delete_service(session: AsyncSession, master_id: UUID, service_id: UUID) -> None:
    repo = ServiceRepository(session)
    service = await repo.get_for_master(service_id, master_id)
    if not service:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Service not found")
    service.is_active = False
    await session.flush()
