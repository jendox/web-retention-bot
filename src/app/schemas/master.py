from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.currency import Currency


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


class WeeklyScheduleRuleIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: str  # "HH:MM"
    end_time: str


class WorkdayOverrideIn(BaseModel):
    override_date: str  # ISO date
    is_closed: bool = False
    start_time: str | None = None
    end_time: str | None = None
    note: str | None = None


class MasterScheduleUpsert(BaseModel):
    weekly_rules: list[WeeklyScheduleRuleIn]
    overrides: list[WorkdayOverrideIn] = []


class MasterScheduleOut(BaseModel):
    weekly_rules: list[dict]
    overrides: list[dict]
