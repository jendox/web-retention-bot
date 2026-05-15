from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_master_profile
from app.core.database import get_db_session
from app.models.master import MasterProfile
from app.repositories.services import ServiceRepository
from app.schemas.service import ServiceCreate, ServiceOut, ServiceUpdate
from app.use_cases.create_service import create_service, delete_service, update_service

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=list[ServiceOut])
async def list_services(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> list[ServiceOut]:
    repo = ServiceRepository(session)
    services = await repo.list_for_master(master.id)
    return [ServiceOut.model_validate(svc) for svc in services]


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
async def post_service(
    payload: ServiceCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> ServiceOut:
    service = await create_service(session, master.id, payload)
    return ServiceOut.model_validate(service)


@router.get("/{service_id}", response_model=ServiceOut)
async def get_service(
    service_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> ServiceOut:
    repo = ServiceRepository(session)
    service = await repo.get_for_master(service_id, master.id)
    if not service:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    return ServiceOut.model_validate(service)


@router.put("/{service_id}", response_model=ServiceOut)
async def put_service(
    service_id: UUID,
    payload: ServiceUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> ServiceOut:
    svc = await update_service(session, master.id, service_id, payload)
    return ServiceOut.model_validate(svc)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_service_route(
    service_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> Response:
    await delete_service(session, master.id, service_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
