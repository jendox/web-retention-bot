from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MessengerCompleteLinkIn(BaseModel):
    token: str = Field(min_length=8, max_length=128)
    external_id: str = Field(min_length=1, max_length=512)
    display_name: str | None = Field(default=None, max_length=256)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "token": "abc123linktoken",
                    "external_id": "123456789",
                    "display_name": "@client_username",
                },
            ],
        },
    )


class MessengerCompleteLinkOut(BaseModel):
    user_id: str
    provider: str
    external_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": "00000000-0000-4000-8000-000000000001",
                    "provider": "telegram",
                    "external_id": "123456789",
                },
            ],
        },
    )
