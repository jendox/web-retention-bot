from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class AnalyticsPeriodPreset(enum.StrEnum):
    CURRENT_MONTH = "current_month"
    LAST_30_DAYS = "last_30_days"
    PREVIOUS_MONTH = "previous_month"


class AnalyticsPeriodOut(BaseModel):
    preset: AnalyticsPeriodPreset | None = None
    from_date: date
    to_date: date
    timezone: str
    range_start: datetime
    range_end: datetime
    label: str


class AnalyticsMoneyOut(BaseModel):
    currency: str
    revenue: Decimal = Field(description="Completed booking revenue.")
    average_check: Decimal = Field(description="Revenue divided by completed visits.")
    lost_revenue: Decimal = Field(description="Potential revenue from cancelled and no-show bookings.")


class AnalyticsSummaryOut(BaseModel):
    completed_count: int
    cancelled_count: int
    no_show_count: int
    unique_clients: int
    new_clients: int
    repeat_clients: int


class AnalyticsDailyMoneyOut(BaseModel):
    currency: str
    revenue: Decimal


class AnalyticsRevenuePointOut(BaseModel):
    date: date
    label: str
    completed_count: int
    money: list[AnalyticsDailyMoneyOut]


class AnalyticsServiceMoneyOut(BaseModel):
    currency: str
    revenue: Decimal
    average_check: Decimal


class AnalyticsServiceOut(BaseModel):
    service_id: UUID
    name: str
    completed_count: int
    cancelled_count: int
    no_show_count: int
    revenue_share_percent: int
    money: list[AnalyticsServiceMoneyOut]


class AnalyticsReturnClientMoneyOut(BaseModel):
    currency: str
    revenue: Decimal


class AnalyticsReturnClientOut(BaseModel):
    client_id: UUID
    display_name: str
    last_visit_at: datetime
    days_since_last_visit: int
    completed_count: int
    note: str
    money: list[AnalyticsReturnClientMoneyOut]


class MasterAnalyticsOut(BaseModel):
    period: AnalyticsPeriodOut
    display_currency: str
    summary: AnalyticsSummaryOut
    money: list[AnalyticsMoneyOut]
    revenue_by_day: list[AnalyticsRevenuePointOut]
    services: list[AnalyticsServiceOut]
    clients_to_return: list[AnalyticsReturnClientOut]
