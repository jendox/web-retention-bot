from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends, status

from app.core.config import Settings, get_settings
from app.repositories.masters import MasterRepository, get_master_repo
from app.repositories.schedules import ScheduleRepository, get_schedule_repo
from app.repositories.services import ServiceRepository, get_service_repo
from app.schemas.availability import SlotOut
from app.schemas.master import MasterProfileSchema
from app.schemas.service import ServiceSchema
from app.services.availability import AvailabilityEngine, get_availability_engine
from app.use_cases.booking.exceptions import AvailabilitySlotsError


def slots_contain(slots: list[datetime], start_at: datetime) -> bool:
    target = start_at.astimezone(UTC).replace(microsecond=0)
    return any(slot.astimezone(UTC).replace(microsecond=0) == target for slot in slots)


def _max_booking_day(today: date, max_advance_days: int) -> date:
    return today + timedelta(days=max_advance_days)


def filter_future_slots_for_day(
    slots: list[datetime],
    *,
    master_profile: MasterProfileSchema,
    calendar_day: date,
    now: datetime,
) -> list[datetime]:
    master_today = master_profile.calendar_day_for_master(now)
    if calendar_day != master_today:
        return slots
    now_utc = now.astimezone(UTC)
    return [slot for slot in slots if slot.astimezone(UTC) > now_utc]


class AvailableSlotsUseCase:
    def __init__(
        self,
        master_repo: MasterRepository,
        service_repo: ServiceRepository,
        schedule_repo: ScheduleRepository,
        availability_engine: AvailabilityEngine,
        settings: Settings,
    ) -> None:
        self._master_repo = master_repo
        self._service_repo = service_repo
        self._schedule_repo = schedule_repo
        self._availability_engine = availability_engine
        self._settings = settings

    async def _get_master_profile(self, master_id: UUID) -> MasterProfileSchema:
        master_profile = await self._master_repo.get_by_master_id(master_id)
        if master_profile is None:
            raise AvailabilitySlotsError(
                status_code=status.HTTP_404_NOT_FOUND, error_message="Master not found",
            )
        return MasterProfileSchema.model_validate(master_profile)

    async def _get_service_for_master(self, service_id: UUID, master_id: UUID) -> ServiceSchema:
        service = await self._service_repo.get_for_master(service_id, master_id)
        if service is None or not service.is_active:
            raise AvailabilitySlotsError(
                status_code=status.HTTP_404_NOT_FOUND, error_message="Service not found or not available",
            )
        return ServiceSchema.model_validate(service)

    @staticmethod
    def _check_calendar_day(
        calendar_day: date,
        master_profile: MasterProfileSchema,
        now: datetime,
        max_advance_days: int,
    ) -> None:
        master_today = master_profile.calendar_day_for_master(now)
        if calendar_day < master_today:
            raise AvailabilitySlotsError(status_code=400, error_message="Date is in the past")
        if calendar_day > _max_booking_day(master_today, max_advance_days):
            raise AvailabilitySlotsError(status_code=400, error_message="Date is outside booking horizon")

    async def __call__(
        self,
        *,
        master_id: UUID,
        service_id: UUID,
        calendar_day: date,
    ) -> list[SlotOut]:
        master_profile = await self._get_master_profile(master_id)

        now = datetime.now(UTC)
        self._check_calendar_day(calendar_day, master_profile, now, self._settings.booking.max_advance_days)

        service = await self._get_service_for_master(service_id, master_id)

        weekly_days = await self._schedule_repo.weekly_days_for_master(master_id)
        date_overrides = await self._schedule_repo.date_overrides_for_master(master_id)

        slots = await self._availability_engine.slots_between(
            master_profile=master_profile,
            service_duration_minutes=service.duration_min,
            day=calendar_day,
            weekly_days=weekly_days,
            date_overrides=date_overrides,
            slot_step_minutes=self._settings.booking.availability_slot_step_minutes,
        )

        slots = filter_future_slots_for_day(
            slots=slots,
            master_profile=master_profile,
            calendar_day=calendar_day,
            now=now,
        )

        return [SlotOut(start_at=slot) for slot in slots]


def get_available_slots_use_case(
    master_repo: Annotated[MasterRepository, Depends(get_master_repo)],
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repo)],
    availability_engine: Annotated[AvailabilityEngine, Depends(get_availability_engine)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AvailableSlotsUseCase:
    return AvailableSlotsUseCase(master_repo, service_repo, schedule_repo, availability_engine, settings)
