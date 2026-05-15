"""Compute bookable timestamps for UI slot pickers."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.schedules import ScheduleRepository
from app.repositories.services import ServiceRepository
from app.services.availability import AvailabilityEngine


async def collect_slots_for_service(
    session: AsyncSession,
    *,
    master,
    service_id,
    calendar_day,
    slot_step_minutes: int,
) -> list[datetime]:
    services = ServiceRepository(session)
    service = await services.get_for_master(service_id, master.id)
    if not service:
        raise ValueError("SERVICE_NOT_FOUND")
    schedules = ScheduleRepository(session)
    weekly_rules = await schedules.weekly_for_master(master.id)
    overrides = await schedules.overrides_for_master(master.id)

    engine = AvailabilityEngine(session, slot_step_minutes=slot_step_minutes)
    return await engine.slots_between(
        master=master,
        service_duration_minutes=service.duration_min,
        day=calendar_day,
        weekly_rules=weekly_rules,
        overrides=overrides,
    )


def calendar_day_for_master(dt: datetime, timezone_name: str):
    tz = ZoneInfo(timezone_name)
    return dt.astimezone(tz).date()


def slots_contain(slots: list[datetime], start_at: datetime) -> bool:
    target = start_at.astimezone(UTC).replace(microsecond=0)
    return any(slot.astimezone(UTC).replace(microsecond=0) == target for slot in slots)
