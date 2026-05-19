from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

_WEEKDAYS = (
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
)
_MONTHS_GENITIVE = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def format_booking_start_local(start_at: datetime, timezone_name: str) -> str:
    if start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=UTC)
    local = start_at.astimezone(ZoneInfo(timezone_name))
    weekday = _WEEKDAYS[local.weekday()]
    month = _MONTHS_GENITIVE[local.month - 1]
    return f"{weekday}, {local.day} {month} {local.year} г., {local:%H:%M}"
