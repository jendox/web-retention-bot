from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

BOOKING_COMMENT_MAX_LENGTH = 500


def normalize_booking_comment(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped


class BookingListScope(enum.StrEnum):
    UPCOMING = "upcoming"
    HISTORY = "history"


class BookingCreate(BaseModel):
    client_id: UUID
    service_id: UUID
    start_at: datetime


class ClientBookingCreate(BaseModel):
    """Client self-service booking against a linked master."""

    master_id: UUID
    service_id: UUID
    start_at: datetime


class BookingOut(BaseModel):
    id: UUID
    master_id: UUID
    client_id: UUID
    service_id: UUID
    start_at: datetime
    end_at: datetime
    duration_min: int
    price_snapshot: Decimal
    currency_snapshot: str
    status: str
    attendance_confirmed_at: datetime | None = None
    cancel_comment: str | None = None
    reschedule_comment: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


class BookingAttendanceMark(BaseModel):
    attended: bool = Field(description="True if the client attended; false for no-show.")


class BookingClientListItem(BookingOut):
    master_display_name: str
    service_name: str


class BookingMonthlyRevenueOut(BaseModel):
    amount: Decimal = Field(description="Sum of price_snapshot for COMPLETED visits in the calendar month.")
    currency: str = Field(description="Master default currency code for display.")
    month: str = Field(description="Calendar month in the master's timezone (YYYY-MM).")
    completed_count: int = Field(description="Number of COMPLETED visits included in the sum.")


class BookingCancel(BaseModel):
    comment: str | None = Field(
        default=None,
        max_length=BOOKING_COMMENT_MAX_LENGTH,
        description="Optional message to the client about the cancellation.",
    )

    @field_validator("comment")
    @classmethod
    def _normalize_comment(cls, value: str | None) -> str | None:
        return normalize_booking_comment(value)


class BookingReschedule(BaseModel):
    start_at: datetime = Field(description="UTC start instant for the reservation")
    comment: str | None = Field(
        default=None,
        max_length=BOOKING_COMMENT_MAX_LENGTH,
        description="Optional message to the client about the reschedule.",
    )

    @field_validator("comment")
    @classmethod
    def _normalize_comment(cls, value: str | None) -> str | None:
        return normalize_booking_comment(value)
