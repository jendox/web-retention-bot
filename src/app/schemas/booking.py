"""Booking shapes."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class BookingCreate(BaseModel):
    client_id: UUID
    service_id: UUID
    start_at: datetime
    invite_token: str | None = Field(default=None, description="Required for guest bookings after invite")


class BookingOut(BaseModel):
    model_config = {"from_attributes": True}

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


class BookingReschedule(BaseModel):
    start_at: datetime = Field(description="UTC start instant for the reservation")
