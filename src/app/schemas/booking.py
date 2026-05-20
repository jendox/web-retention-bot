from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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

    model_config = ConfigDict(
        from_attributes=True,
    )


class BookingAttendanceMark(BaseModel):
    attended: bool = Field(description="True if the client attended; false for no-show.")


class BookingClientListItem(BookingOut):
    master_display_name: str
    service_name: str


class BookingReschedule(BaseModel):
    start_at: datetime = Field(description="UTC start instant for the reservation")
