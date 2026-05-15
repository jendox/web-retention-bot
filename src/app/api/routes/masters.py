from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_master_profile
from app.core.database import get_db_session
from app.repositories.schedules import ScheduleRepository
from app.schemas.master import (
    MasterProfileSchema,
    MasterProfileUpdate,
    MasterScheduleOut,
    MasterScheduleUpsert,
)
from app.use_cases.replace_schedule import replace_master_schedule

router = APIRouter(prefix="/masters", tags=["masters"])


async def _snapshot_schedule(session: AsyncSession, master_id: UUID) -> MasterScheduleOut:
    schedules = ScheduleRepository(session)
    weekly_models = await schedules.weekly_for_master(master_id)
    overrides_models = await schedules.overrides_for_master(master_id)

    weekly_rules = sorted(
        [
            {
                "weekday": rule.weekday,
                "start_time": rule.start_time.strftime("%H:%M"),
                "end_time": rule.end_time.strftime("%H:%M"),
            }
            for rule in weekly_models
        ],
        key=lambda item: (item["weekday"], item["start_time"]),
    )
    overrides = sorted(
        [
            {
                "override_date": ov.override_date.isoformat(),
                "is_closed": ov.is_closed,
                "start_time": ov.start_time.strftime("%H:%M") if ov.start_time else None,
                "end_time": ov.end_time.strftime("%H:%M") if ov.end_time else None,
                "note": ov.note,
            }
            for ov in overrides_models
        ],
        key=lambda item: item["override_date"],
    )
    return MasterScheduleOut(weekly_rules=weekly_rules, overrides=overrides)


@router.get("/me", response_model=MasterProfileSchema)
async def profile_me(master: Annotated[MasterProfileSchema, Depends(require_master_profile)]) -> MasterProfileSchema:
    return MasterProfileSchema.model_validate(master)


@router.put("/me", response_model=MasterProfileSchema)
async def profile_update(
    payload: MasterProfileUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    master: Annotated[MasterProfileSchema, Depends(require_master_profile)],
) -> MasterProfileSchema:
    if payload.display_name:
        master.display_name = payload.display_name
    if payload.public_slug is not None:
        master.public_slug = payload.public_slug
    if payload.timezone:
        master.timezone = payload.timezone
    await session.flush()
    return MasterProfileSchema.model_validate(master)


@router.get("/me/schedule", response_model=MasterScheduleOut)
async def get_schedule_route(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    master: Annotated[MasterProfileSchema, Depends(require_master_profile)],
) -> MasterScheduleOut:
    return await _snapshot_schedule(session, master.id)


@router.put("/me/schedule", response_model=MasterScheduleOut)
async def put_schedule_route(
    payload: MasterScheduleUpsert,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    master: Annotated[MasterProfileSchema, Depends(require_master_profile)],
) -> MasterScheduleOut:
    try:
        await replace_master_schedule(
            session,
            master.id,
            weekly=payload.weekly_rules,
            overrides=payload.overrides,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await _snapshot_schedule(session, master.id)
