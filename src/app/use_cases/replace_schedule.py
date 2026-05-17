"""Replace weekly rules + overrides in one transaction."""

from datetime import UTC, date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.structured_logging import get_logger, log_context
from app.models.booking import Booking, BookingStatus
from app.models.schedule import WeeklyScheduleRule, WorkdayOverride, WorkdayOverrideInterval
from app.repositories.bookings import BookingRepository
from app.repositories.schedules import ScheduleRepository
from app.schemas.master import WeeklyScheduleRuleIn, WorkdayOverrideIn
from app.services.availability import parse_clock, windows_for_date

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
    weekly: list[WeeklyScheduleRule],
    overrides: list[WorkdayOverride],
    timezone_name: str,
) -> bool:
    tz = ZoneInfo(timezone_name)
    start_local = _aware_utc(booking.start_at).astimezone(tz)
    end_local = _aware_utc(booking.end_at).astimezone(tz)
    windows = windows_for_date(start_local.date(), weekly, overrides, tz)
    return any(window_start <= start_local and end_local <= window_end for window_start, window_end in windows)


async def _ensure_existing_bookings_still_fit(
    session: AsyncSession,
    master_id: UUID,
    timezone_name: str,
    weekly: list[WeeklyScheduleRule],
    overrides: list[WorkdayOverride],
) -> None:
    bookings = await BookingRepository(session).list_for_master(master_id)
    now = datetime.now(UTC)
    conflicts = [
        booking
        for booking in bookings
        if booking.status == BookingStatus.scheduled
        and _aware_utc(booking.start_at) >= now
        and not booking_fits_schedule(booking, weekly, overrides, timezone_name)
    ]
    if conflicts:
        logger.warning("failed", reason="schedule_booking_conflict", booking_count=len(conflicts))
        raise ScheduleBookingConflictError(conflicts)


async def replace_master_schedule(
    session: AsyncSession,
    master_id: UUID,
    timezone_name: str,
    *,
    weekly: list[WeeklyScheduleRuleIn],
    overrides: list[WorkdayOverrideIn],
) -> None:
    with log_context(use_case="replace_master_schedule", master_id=str(master_id)):
        schedule_repo = ScheduleRepository(session)

        weekly_models: list[WeeklyScheduleRule] = []
        for day in weekly:
            for interval in day.intervals:
                weekly_models.append(
                    WeeklyScheduleRule(
                        master_id=master_id,
                        weekday=day.weekday,
                        start_time=parse_clock(interval.start_time),
                        end_time=parse_clock(interval.end_time),
                    ),
                )

        override_models: list[WorkdayOverride] = []
        for ov in overrides:
            parsed_date = date.fromisoformat(ov.override_date)
            override = WorkdayOverride(
                master_id=master_id,
                override_date=parsed_date,
                is_closed=ov.is_closed,
                note=ov.note,
            )
            override.intervals = [
                WorkdayOverrideInterval(
                    start_time=parse_clock(interval.start_time),
                    end_time=parse_clock(interval.end_time),
                    sort_order=index,
                )
                for index, interval in enumerate(ov.intervals)
            ]
            override_models.append(override)

        await _ensure_existing_bookings_still_fit(session, master_id, timezone_name, weekly_models, override_models)
        await schedule_repo.replace_weekly_rules(master_id, weekly_models)
        await schedule_repo.replace_overrides(master_id, override_models)
        await session.flush()
        logger.info("replaced", weekly_count=len(weekly_models), override_count=len(override_models))


__all__ = ["ScheduleBookingConflictError", "booking_fits_schedule", "replace_master_schedule"]
