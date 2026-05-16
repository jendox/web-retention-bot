from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserSchema(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime
    email_verified: bool
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )
