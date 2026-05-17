from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.currency import Currency

CLOCK_PARTS_COUNT = 2
MAX_HOUR = 23
MAX_MINUTE = 59


class MasterProfileSchema(BaseModel):
    id: UUID
    display_name: str
    public_slug: str | None
    timezone: str
    default_currency: Currency

    model_config = ConfigDict(
        from_attributes=True,
    )


class MasterProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    public_slug: str | None = Field(default=None, max_length=80)
    timezone: str | None = Field(default=None, max_length=64)
    default_currency: Currency | None = None


class ScheduleInterval(BaseModel):
    start_time: str  # "HH:MM"
    end_time: str


def _clock_minutes(value: str) -> int:
    parts = value.strip().split(":")
    if len(parts) != CLOCK_PARTS_COUNT:
        msg = "Time must use HH:MM format."
        raise ValueError(msg)
    hour = int(parts[0])
    minute = int(parts[1])
    if hour < 0 or hour > MAX_HOUR or minute < 0 or minute > MAX_MINUTE:
        msg = "Time must use HH:MM format."
        raise ValueError(msg)
    return hour * 60 + minute


def _validate_intervals(intervals: list[ScheduleInterval]) -> list[ScheduleInterval]:
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


class WeeklyScheduleRuleIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    intervals: list[ScheduleInterval] = Field(default_factory=list)

    @field_validator("intervals")
    @classmethod
    def validate_intervals(cls, value: list[ScheduleInterval]) -> list[ScheduleInterval]:
        return _validate_intervals(value)


class WorkdayOverrideIn(BaseModel):
    override_date: str  # ISO date
    is_closed: bool = False
    intervals: list[ScheduleInterval] = Field(default_factory=list)
    note: str | None = None

    @field_validator("intervals")
    @classmethod
    def validate_intervals(cls, value: list[ScheduleInterval]) -> list[ScheduleInterval]:
        return _validate_intervals(value)

    @model_validator(mode="after")
    def validate_closed_day(self) -> WorkdayOverrideIn:
        if self.is_closed and self.intervals:
            msg = "Closed override must not contain intervals."
            raise ValueError(msg)
        if not self.is_closed and not self.intervals:
            msg = "Working override requires at least one interval."
            raise ValueError(msg)
        return self


class MasterScheduleUpsert(BaseModel):
    weekly_rules: list[WeeklyScheduleRuleIn]
    overrides: list[WorkdayOverrideIn] = []

    @model_validator(mode="after")
    def validate_unique_days(self) -> MasterScheduleUpsert:
        weekdays = [item.weekday for item in self.weekly_rules]
        if len(weekdays) != len(set(weekdays)):
            msg = "Weekly schedule must contain each weekday at most once."
            raise ValueError(msg)
        override_dates = [item.override_date for item in self.overrides]
        if len(override_dates) != len(set(override_dates)):
            msg = "Schedule overrides must contain each date at most once."
            raise ValueError(msg)
        return self


class MasterScheduleOut(BaseModel):
    weekly_rules: list[dict]
    overrides: list[dict]
