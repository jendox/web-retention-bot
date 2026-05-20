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
