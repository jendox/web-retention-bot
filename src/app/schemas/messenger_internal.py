from __future__ import annotations

from pydantic import BaseModel, Field


class MessengerCompleteLinkIn(BaseModel):
    token: str = Field(min_length=8, max_length=128)
    external_id: str = Field(min_length=1, max_length=512)
    display_name: str | None = Field(default=None, max_length=256)


class MessengerCompleteLinkOut(BaseModel):
    user_id: str
    provider: str
    external_id: str
