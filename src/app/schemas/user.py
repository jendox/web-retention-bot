from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, model_validator

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

    @model_validator(mode="after")
    def set_email_verified(self) -> UserSchema:
        self.email_verified = self.email_verified_at is not None
        return self


class UserMeOut(UserSchema):
    """Профиль сессии: данные карточки клиента (если пользователь привязан к мастеру)."""

    client_display_name: str | None = None
    client_phone: str | None = None
    client_timezone: str | None = None
