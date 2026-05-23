from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.models import MasterProfile, Service
from app.repositories.masters import MasterRepository, get_master_repo
from app.repositories.schedules import ScheduleRepository, get_schedule_repo
from app.repositories.services import ServiceRepository, get_service_repo
from app.schemas.availability import SlotOut
from app.schemas.master import MasterProfileSchema
from app.services.availability import AvailabilityEngine, get_availability_engine
from app.use_cases.booking.exceptions import (
    AvailabilityDateInPastError,
    AvailabilityDateOutsideHorizonError,
    AvailabilityMasterNotFoundError,
    AvailabilityServiceNotFoundError,
)


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


def _master_days_for_viewer_day(
    *,
    viewer_day: date,
    viewer_timezone: ZoneInfo,
    master_timezone: ZoneInfo,
) -> list[date]:
    viewer_start = datetime.combine(viewer_day, datetime.min.time(), tzinfo=viewer_timezone)
    viewer_end = viewer_start + timedelta(days=1) - timedelta(microseconds=1)
    start_master_day = viewer_start.astimezone(master_timezone).date()
    end_master_day = viewer_end.astimezone(master_timezone).date()
    if start_master_day == end_master_day:
        return [start_master_day]
    return [start_master_day, end_master_day]


def _filter_slots_for_viewer_day(
    slots: list[datetime],
    *,
    viewer_day: date,
    viewer_timezone: ZoneInfo,
) -> list[datetime]:
    return [slot for slot in slots if slot.astimezone(viewer_timezone).date() == viewer_day]


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

    async def _get_master_profile(self, master_id: UUID) -> MasterProfile:
        master_profile = await self._master_repo.get_by_master_id(master_id)
        if master_profile is None:
            raise AvailabilityMasterNotFoundError()
        return master_profile

    async def _get_service_for_master(self, service_id: UUID, master_id: UUID) -> Service:
        service = await self._service_repo.get_for_master(service_id, master_id)
        if service is None or not service.is_active:
            raise AvailabilityServiceNotFoundError()
        return service

    @staticmethod
    def _check_calendar_day(
        calendar_day: date,
        master_profile: MasterProfileSchema,
        now: datetime,
        max_advance_days: int,
    ) -> None:
        master_today = master_profile.calendar_day_for_master(now)
        if calendar_day < master_today:
            raise AvailabilityDateInPastError()
        if calendar_day > _max_booking_day(master_today, max_advance_days):
            raise AvailabilityDateOutsideHorizonError()

    async def _slots_for_days(
        self,
        *,
        days: list[date],
        master_profile: MasterProfileSchema,
        service: Service,
        schedules: tuple[list, list],
        now: datetime,
        viewer_mode: bool,
    ) -> list[datetime]:
        weekly_days, date_overrides = schedules
        slots: list[datetime] = []
        valid_day_found = False
        skipped_error: Exception | None = None

        for day in days:
            try:
                self._check_calendar_day(day, master_profile, now, self._settings.booking.max_advance_days)
            except (AvailabilityDateInPastError, AvailabilityDateOutsideHorizonError) as exc:
                if viewer_mode:
                    skipped_error = skipped_error or exc
                    continue
                raise
            valid_day_found = True

            day_slots = await self._availability_engine.slots_between(
                master_profile=master_profile,
                service_duration_minutes=service.duration_min,
                day=day,
                weekly_days=weekly_days,
                date_overrides=date_overrides,
                slot_step_minutes=self._settings.booking.availability_slot_step_minutes,
            )
            slots.extend(
                filter_future_slots_for_day(
                    slots=day_slots,
                    master_profile=master_profile,
                    calendar_day=day,
                    now=now,
                ),
            )

        if viewer_mode and not valid_day_found and skipped_error is not None:
            raise skipped_error

        return slots

    async def __call__(
        self,
        *,
        master_id: UUID,
        service_id: UUID,
        calendar_day: date,
        viewer_timezone: str | None = None,
    ) -> list[SlotOut]:
        master_profile_model = await self._get_master_profile(master_id)
        master_profile = MasterProfileSchema.model_validate(master_profile_model)

        now = datetime.now(UTC)
        if viewer_timezone is None:
            self._check_calendar_day(calendar_day, master_profile, now, self._settings.booking.max_advance_days)

        service = await self._get_service_for_master(service_id, master_id)

        weekly_days = await self._schedule_repo.weekly_days_for_master(master_id)
        date_overrides = await self._schedule_repo.date_overrides_for_master(master_id)

        days = [calendar_day]
        viewer_tz: ZoneInfo | None = None
        if viewer_timezone is not None:
            viewer_tz = ZoneInfo(viewer_timezone)
            days = _master_days_for_viewer_day(
                viewer_day=calendar_day,
                viewer_timezone=viewer_tz,
                master_timezone=master_profile.tzinfo,
            )

        slots = await self._slots_for_days(
            days=days,
            master_profile=master_profile,
            service=service,
            schedules=(weekly_days, date_overrides),
            now=now,
            viewer_mode=viewer_tz is not None,
        )
        if viewer_tz is not None:
            slots = _filter_slots_for_viewer_day(
                slots=slots,
                viewer_day=calendar_day,
                viewer_timezone=viewer_tz,
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
