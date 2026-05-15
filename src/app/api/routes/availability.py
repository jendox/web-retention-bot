from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.repositories.masters import MasterRepository
from app.repositories.services import ServiceRepository
from app.schemas.availability import SlotOut
from app.use_cases.list_available_slots import collect_slots_for_service

router = APIRouter(prefix="/availability", tags=["availability"])


@router.get("", response_model=list[SlotOut])
async def availability_slots(
    master_id: Annotated[UUID, Query()],
    service_id: Annotated[UUID, Query()],
    day: Annotated[date, Query(alias="date")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[SlotOut]:
    masters = MasterRepository(session)
    services = ServiceRepository(session)
    master_profile = await masters.get(master_id)
    if not master_profile:
        raise HTTPException(status_code=404, detail="Master not found")
    svc = await services.get_for_master(service_id, master_id)
    if not svc or not svc.is_active:
        raise HTTPException(status_code=404, detail="Service not available")
    settings = get_settings()
    slots = await collect_slots_for_service(
        session,
        master=master_profile,
        service_id=svc.id,
        calendar_day=day,
        slot_step_minutes=settings.AVAILABILITY_SLOT_STEP_MINUTES,
    )
    return [SlotOut(start_at=slot) for slot in slots]
