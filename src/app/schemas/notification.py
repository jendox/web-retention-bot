from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserNotificationOut(BaseModel):
    id: UUID
    event_type: str
    title: str
    body: str
    link_url: str | None
    read_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserNotificationsListOut(BaseModel):
    items: list[UserNotificationOut]
    total: int
    page: int
    page_size: int
    unread_count: int

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": "00000000-0000-4000-8000-000000000001",
                            "event_type": "booking.created",
                            "title": "Новая запись",
                            "body": "Клиент записался на услугу.",
                            "link_url": "/master/bookings",
                            "read_at": None,
                            "created_at": "2026-05-23T12:00:00Z",
                        },
                    ],
                    "total": 1,
                    "page": 1,
                    "page_size": 20,
                    "unread_count": 1,
                },
            ],
        },
    )
