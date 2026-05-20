from __future__ import annotations

from datetime import date, datetime, time
from typing import Self
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from app.core.currency import Currency

__all__ = [
    "MasterProfileSchema",
    "MasterProfileUpdate",
    "ScheduleIntervalIn",
    "WeeklyScheduleDayIn",
    "ScheduleDateOverrideIn",
    "MasterScheduleUpsert",
    "ScheduleIntervalOut",
    "WeeklyScheduleDayOut",
    "ScheduleDateOverrideOut",
    "MasterScheduleOut",
]


class MasterProfileSchema(BaseModel):
    id: UUID
    display_name: str
    public_slug: str | None
    timezone: str
    default_currency: Currency | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    telegram: str | None = None
    viber: str | None = None

    tzinfo: ZoneInfo | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )

    @model_validator(mode="after")
    def set_zone_info(self) -> MasterProfileSchema:
        self.tzinfo = ZoneInfo(self.timezone)
        return self

    def calendar_day_for_master(self, dt: datetime) -> date:
        return dt.astimezone(self.tzinfo).date()


class MasterProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    public_slug: str | None = Field(default=None, max_length=80)
    timezone: str | None = Field(default=None, max_length=64)
    default_currency: Currency | None = None
    contact_email: str | None = Field(default=None, max_length=320)
    contact_phone: str | None = Field(default=None, max_length=50)
    telegram: str | None = Field(default=None, max_length=100)
    viber: str | None = Field(default=None, max_length=100)

    @field_validator("contact_email", mode="before")
    @classmethod
    def empty_contact_email_to_none(cls, value: str | None) -> str | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("contact_phone", "telegram", "viber", mode="before")
    @classmethod
    def empty_optional_str_to_none(cls, value: str | None) -> str | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return value.strip() if isinstance(value, str) else value


class ScheduleIntervalIn(BaseModel):
    start_time: time
    end_time: time

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_minute_precision(cls, value: time) -> time:
        if value.second or value.microsecond:
            msg = "Time must use HH:MM precision."
            raise ValueError(msg)
        return value


def _clock_minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _validate_intervals(intervals: list[ScheduleIntervalIn]) -> list[ScheduleIntervalIn]:
    ordered = sorted(intervals, key=lambda item: _clock_minutes(item.start_time))
    previous_end: int | None = None
    for interval in ordered:
        start = _clock_minutes(interval.start_time)
        end = _clock_minutes(interval.end_time)
        if start >= end:
            msg = "Schedule interval start_time must be before end_time."
            raise ValueError(msg)
        if previous_end is not None and start < previous_end:
            msg = "Schedule intervals must not overlap."
            raise ValueError(msg)
        previous_end = end
    return ordered


class BaseScheduleDay(BaseModel):
    is_closed: bool = False
    intervals: list[ScheduleIntervalIn] = Field(default_factory=list)
    note: str | None = None

    @field_validator("intervals")
    @classmethod
    def validate_intervals(cls, value: list[ScheduleIntervalIn]) -> list[ScheduleIntervalIn]:
        return _validate_intervals(value)

    @model_validator(mode="after")
    def validate_closed_day(self) -> Self:
        if self.is_closed and self.intervals:
            msg = "Closed day must not contain intervals."
            raise ValueError(msg)
        if not self.is_closed and not self.intervals:
            msg = "Working day requires at least one interval."
            raise ValueError(msg)
        return self


class WeeklyScheduleDayIn(BaseScheduleDay):
    weekday: int = Field(ge=0, le=6)


class ScheduleDateOverrideIn(BaseScheduleDay):
    schedule_date: date


class MasterScheduleUpsert(BaseModel):
    weekly_days: list[WeeklyScheduleDayIn]
    date_overrides: list[ScheduleDateOverrideIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_days(self) -> MasterScheduleUpsert:
        weekdays = [item.weekday for item in self.weekly_days]
        if len(weekdays) != len(set(weekdays)):
            msg = "Weekly schedule must contain each weekday at most once."
            raise ValueError(msg)
        override_dates = [item.schedule_date for item in self.date_overrides]
        if len(override_dates) != len(set(override_dates)):
            msg = "Schedule overrides must contain each date at most once."
            raise ValueError(msg)
        return self


class ScheduleIntervalOut(BaseModel):
    start_time: time
    end_time: time

    model_config = ConfigDict(
        from_attributes=True,
    )

    @field_serializer("start_time", "end_time")
    def serialize_clock(self, value: time) -> str:
        return value.strftime("%H:%M")


class WeeklyScheduleDayOut(BaseModel):
    weekday: int
    is_closed: bool
    intervals: list[ScheduleIntervalOut]
    note: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


class ScheduleDateOverrideOut(BaseModel):
    schedule_date: date
    is_closed: bool
    intervals: list[ScheduleIntervalOut]
    note: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


class MasterScheduleOut(BaseModel):
    weekly_days: list[WeeklyScheduleDayOut]
    date_overrides: list[ScheduleDateOverrideOut]
