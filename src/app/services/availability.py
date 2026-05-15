"""Generate candidate slots from schedule + bookings."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.master import MasterProfile
from app.models.schedule import WeeklyScheduleRule, WorkdayOverride
from app.repositories.bookings import BookingRepository


def _combine_local(d: date, t: time, tz: ZoneInfo) -> datetime:
    return datetime.combine(d, t, tzinfo=tz)


def parse_clock(value: str) -> time:
    hour_str, minute_str = value.strip().split(":", maxsplit=1)
    return time(int(hour_str), int(minute_str))


def _windows_for_date(
    target: date,
    weekly: list[WeeklyScheduleRule],
    overrides: list[WorkdayOverride],
    tz: ZoneInfo,
) -> list[tuple[datetime, datetime]]:
    override_for_day = next((o for o in overrides if o.override_date == target), None)
    if override_for_day and override_for_day.is_closed:
        return []

    weekday = target.weekday()
    baseline = [r for r in weekly if r.weekday == weekday]
    segments: list[tuple[datetime, datetime]] = []
    if override_for_day and override_for_day.start_time and override_for_day.end_time:
        start_dt = _combine_local(target, override_for_day.start_time, tz)
        end_dt = _combine_local(target, override_for_day.end_time, tz)
        if end_dt <= start_dt:
            return []
        segments.append((start_dt, end_dt))
    else:
        for rule in baseline:
            start_dt = _combine_local(target, rule.start_time, tz)
            end_dt = _combine_local(target, rule.end_time, tz)
            if end_dt <= start_dt:
                continue
            segments.append((start_dt, end_dt))
    segments.sort(key=lambda pair: pair[0])
    return segments


class AvailabilityEngine:
    def __init__(
        self,
        session: AsyncSession,
        *,
        slot_step_minutes: int,
    ) -> None:
        self.session = session
        self.slot_step_minutes = slot_step_minutes
        self.bookings = BookingRepository(session)

    async def slots_between(
        self,
        *,
        master: MasterProfile,
        service_duration_minutes: int,
        day: date,
        weekly_rules: list[WeeklyScheduleRule],
        overrides: list[WorkdayOverride],
    ) -> list[datetime]:
        tzinfo = ZoneInfo(master.timezone)
        windows_local = _windows_for_date(day, weekly_rules, overrides, tzinfo)
        day_start_local = datetime.combine(day, time.min, tzinfo=tzinfo)
        day_end_local = day_start_local + timedelta(days=1)
        range_start = day_start_local.astimezone(UTC).replace(tzinfo=UTC)
        range_end = day_end_local.astimezone(UTC).replace(tzinfo=UTC)
        bookings = await self.bookings.active_between(master.id, range_start, range_end)

        increment = timedelta(minutes=self.slot_step_minutes)
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

    def _conflicts(self, bookings: list[Booking], start_at: datetime, end_at: datetime) -> bool:
        for booking in bookings:
            if booking.start_at < end_at and booking.end_at > start_at:
                return True
        return False


__all__ = ["AvailabilityEngine", "parse_clock"]
