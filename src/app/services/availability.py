from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends

from app.models.booking import Booking
from app.models.schedule import ScheduleDateOverride, WeeklyScheduleDay
from app.repositories.bookings import BookingRepository, get_booking_repo
from app.schemas.master import MasterProfileSchema

__all__ = [
    "AvailabilityEngine",
    "get_availability_engine",
    "windows_for_date",
]


def _combine_local(d: date, t: time, tz: ZoneInfo) -> datetime:
    return datetime.combine(d, t, tzinfo=tz)


def _process_override_for_day(
    target: date,
    override_for_day: ScheduleDateOverride,
    tz: ZoneInfo,
) -> list[tuple[datetime, datetime]]:
    segments: list[tuple[datetime, datetime]] = []
    for interval in override_for_day.intervals:
        start_dt = _combine_local(target, interval.start_time, tz)
        end_dt = _combine_local(target, interval.end_time, tz)
        if end_dt <= start_dt:
            continue
        segments.append((start_dt, end_dt))
    return segments


def _process_weekly_days(
    target: date,
    weekly_days: list[WeeklyScheduleDay],
    tz: ZoneInfo,
) -> list[tuple[datetime, datetime]]:
    segments: list[tuple[datetime, datetime]] = []
    weekly_day = next((item for item in weekly_days if item.weekday == target.weekday()), None)
    if weekly_day is None or weekly_day.is_closed:
        return []
    for interval in weekly_day.intervals:
        start_dt = _combine_local(target, interval.start_time, tz)
        end_dt = _combine_local(target, interval.end_time, tz)
        if end_dt <= start_dt:
            continue
        segments.append((start_dt, end_dt))
    return segments


def windows_for_date(
    target: date,
    weekly_days: list[WeeklyScheduleDay],
    date_overrides: list[ScheduleDateOverride],
    tz: ZoneInfo,
) -> list[tuple[datetime, datetime]]:
    override_for_day = next((o for o in date_overrides if o.schedule_date == target), None)
    if override_for_day and override_for_day.is_closed:
        return []

    if override_for_day:
        segments = _process_override_for_day(target, override_for_day, tz)
    else:
        segments = _process_weekly_days(target, weekly_days, tz)

    segments.sort(key=lambda pair: pair[0])
    return segments


class AvailabilityEngine:
    def __init__(self, booking_repo: BookingRepository) -> None:
        self._booking_repo = booking_repo

    async def slots_between(
        self,
        *,
        master_profile: MasterProfileSchema,
        service_duration_minutes: int,
        day: date,
        weekly_days: list[WeeklyScheduleDay],
        date_overrides: list[ScheduleDateOverride],
        slot_step_minutes: int,
    ) -> list[datetime]:
        windows_local = windows_for_date(day, weekly_days, date_overrides, master_profile.tzinfo)
        day_start_local = datetime.combine(day, time.min, tzinfo=master_profile.tzinfo)
        day_end_local = day_start_local + timedelta(days=1)
        range_start = day_start_local.astimezone(UTC).replace(tzinfo=UTC)
        range_end = day_end_local.astimezone(UTC).replace(tzinfo=UTC)
        bookings = await self._booking_repo.active_between(master_profile.id, range_start, range_end)

        increment = timedelta(minutes=slot_step_minutes)
        duration_delta = timedelta(minutes=service_duration_minutes)

        slots: list[datetime] = []
        for win_start_local, win_end_local in windows_local:
            cursor = win_start_local
            while cursor + duration_delta <= win_end_local:
                utc_start = cursor.astimezone(UTC).replace(tzinfo=UTC)
                utc_end = (cursor + duration_delta).astimezone(UTC).replace(tzinfo=UTC)
                if not self._conflicts(bookings, utc_start, utc_end):
                    slots.append(utc_start)
                cursor += increment

        return slots

    @staticmethod
    def _conflicts(bookings: list[Booking], start_at: datetime, end_at: datetime) -> bool:
        for booking in bookings:
            if booking.start_at < end_at and booking.end_at > start_at:
                return True
        return False


def get_availability_engine(
    bookings_repo: Annotated[BookingRepository, Depends(get_booking_repo)],
) -> AvailabilityEngine:
    return AvailabilityEngine(bookings_repo)
