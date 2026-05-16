from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.core.structured_logging import get_logger

logger = get_logger("user_schema")


class UserSchema(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime
    email_verified_at: datetime | None = None
    email_verified: bool = False
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )

    @field_validator("email_verified", mode="before")
    @classmethod
    def email_verified_validator(cls, value: Any):
        if cls.email_verified_at is not None:
            return True
        return value
