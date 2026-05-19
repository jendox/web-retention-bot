from __future__ import annotations

from datetime import time
from uuid import UUID

from app.models import WeeklyScheduleDay, WeeklyScheduleInterval

DEFAULT_WORKING_WEEKDAYS = range(5)
DEFAULT_WORKDAY_START = time(10, 0)
DEFAULT_WORKDAY_END = time(18, 0)


def default_weekly_schedule_days(master_id: UUID) -> list[WeeklyScheduleDay]:
    days: list[WeeklyScheduleDay] = []
    for weekday in DEFAULT_WORKING_WEEKDAYS:
        day = WeeklyScheduleDay(
            master_id=master_id,
            weekday=weekday,
            is_closed=False,
        )
        day.intervals = [
            WeeklyScheduleInterval(
                start_time=DEFAULT_WORKDAY_START,
                end_time=DEFAULT_WORKDAY_END,
                sort_order=0,
            ),
        ]
        days.append(day)
    return days
