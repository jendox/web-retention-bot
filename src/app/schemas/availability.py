"""Availability query + response."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class AvailabilityQuery(BaseModel):
    master_id: UUID
    service_id: UUID
    booking_day: date


class SlotOut(BaseModel):
    start_at: datetime
