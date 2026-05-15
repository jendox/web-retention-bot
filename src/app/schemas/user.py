from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import User as UserModel


class UserSchema(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime
    email_verified: bool
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )

    @classmethod
    def from_model(cls, user: UserModel) -> Self:
        return cls(
            id=user.id,
            email=user.email,
            created_at=user.created_at,
            email_verified=user.email_verified_at is not None,
            is_active=user.is_active,
        )
