from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AvailabilityQuery(BaseModel):
    master_id: UUID
    service_id: UUID
    booking_day: date


class SlotOut(BaseModel):
    start_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"start_at": "2026-05-24T09:00:00Z"},
                {"start_at": "2026-05-24T09:30:00Z"},
            ],
        },
    )
