from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models.booking import Booking, BookingStatus
from app.models.master import MasterProfile
from app.models.schedule import (
    ScheduleDateOverride,
    ScheduleDateOverrideInterval,
    WeeklyScheduleDay,
    WeeklyScheduleInterval,
)
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.repositories.schedules import ScheduleRepository, get_schedule_repo
from app.schemas.master import MasterScheduleOut, MasterScheduleUpsert
from app.services.availability import windows_for_date
from app.use_cases.schedule.get_schedule import GetMasterScheduleUseCase, get_get_master_schedule_use_case

__all__ = [
    "ReplaceMasterScheduleUseCase",
    "ScheduleBookingConflictError",
    "booking_fits_schedule",
    "get_replace_master_schedule_use_case",
]

logger = get_logger("app.schedule")


class ScheduleBookingConflictError(Exception):
    def __init__(self, conflicts: list[Booking]) -> None:
        self.conflicts = conflicts
        super().__init__("Schedule changes affect existing bookings.")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def booking_fits_schedule(
    booking: Booking,
    weekly_days: list[WeeklyScheduleDay],
    date_overrides: list[ScheduleDateOverride],
    timezone_name: str,
) -> bool:
    tz = ZoneInfo(timezone_name)
    start_local = _aware_utc(booking.start_at).astimezone(tz)
    end_local = _aware_utc(booking.end_at).astimezone(tz)
    windows = windows_for_date(start_local.date(), weekly_days, date_overrides, tz)
    return any(window_start <= start_local and end_local <= window_end for window_start, window_end in windows)


class ReplaceMasterScheduleUseCase:
    def __init__(
        self,
        schedule_repo: ScheduleRepository,
        booking_repo: BookingRepository,
        get_schedule_use_case: GetMasterScheduleUseCase,
    ) -> None:
        self._schedule_repo = schedule_repo
        self._booking_repo = booking_repo
        self._get_schedule_use_case = get_schedule_use_case

    async def _ensure_existing_bookings_still_fit(
        self,
        master: MasterProfile,
        weekly_days: list[WeeklyScheduleDay],
        date_overrides: list[ScheduleDateOverride],
    ) -> None:
        bookings = await self._booking_repo.list_for_master(master.id)
        now = datetime.now(UTC)
        conflicts = [
            booking
            for booking in bookings
            if booking.status == BookingStatus.scheduled
            and _aware_utc(booking.start_at) >= now
            and not booking_fits_schedule(booking, weekly_days, date_overrides, master.timezone)
        ]
        if conflicts:
            logger.warning("failed", reason="schedule_booking_conflict", booking_count=len(conflicts))
            raise ScheduleBookingConflictError(conflicts)

    @staticmethod
    def _weekly_day_models(master_id: UUID, payload: MasterScheduleUpsert) -> list[WeeklyScheduleDay]:
        weekly_models: list[WeeklyScheduleDay] = []
        for day in payload.weekly_days:
            weekly_day = WeeklyScheduleDay(
                master_id=master_id,
                weekday=day.weekday,
                is_closed=day.is_closed,
                note=day.note,
            )
            weekly_day.intervals = [
                WeeklyScheduleInterval(
                    start_time=interval.start_time,
                    end_time=interval.end_time,
                    sort_order=index,
                )
                for index, interval in enumerate(day.intervals)
            ]
            weekly_models.append(weekly_day)
        return weekly_models

    @staticmethod
    def _date_override_models(master_id: UUID, payload: MasterScheduleUpsert) -> list[ScheduleDateOverride]:
        override_models: list[ScheduleDateOverride] = []
        for ov in payload.date_overrides:
            override = ScheduleDateOverride(
                master_id=master_id,
                schedule_date=ov.schedule_date,
                is_closed=ov.is_closed,
                note=ov.note,
            )
            override.intervals = [
                ScheduleDateOverrideInterval(
                    start_time=interval.start_time,
                    end_time=interval.end_time,
                    sort_order=index,
                )
                for index, interval in enumerate(ov.intervals)
            ]
            override_models.append(override)
        return override_models

    async def __call__(self, master: MasterProfile, payload: MasterScheduleUpsert) -> MasterScheduleOut:
        with log_context(use_case="replace_master_schedule", master_id=str(master.id)):
            weekly_models = self._weekly_day_models(master.id, payload)
            override_models = self._date_override_models(master.id, payload)

            await self._ensure_existing_bookings_still_fit(master, weekly_models, override_models)
            await self._schedule_repo.replace_weekly_days(master.id, weekly_models)
            await self._schedule_repo.replace_date_overrides(master.id, override_models)
            await self._schedule_repo.flush()
            logger.info("replaced", weekly_day_count=len(weekly_models), date_override_count=len(override_models))
            return await self._get_schedule_use_case(master.id)


def get_replace_master_schedule_use_case(
    schedule_repo: Annotated[ScheduleRepository, Depends(get_schedule_repo)],
    booking_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
    get_schedule_use_case: Annotated[GetMasterScheduleUseCase, Depends(get_get_master_schedule_use_case)],
) -> ReplaceMasterScheduleUseCase:
    return ReplaceMasterScheduleUseCase(schedule_repo, booking_repo, get_schedule_use_case)
