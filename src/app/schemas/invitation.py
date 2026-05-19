from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.service import ServiceSchema

DEFAULT_INVITATION_TOKEN_EXPIRES_HOURS = 72


class InvitationCreate(BaseModel):
    expires_hours: int = Field(default=DEFAULT_INVITATION_TOKEN_EXPIRES_HOURS, ge=1, le=24 * 30)
    target_email: EmailStr | None = None
    target_client_id: UUID | None = None
    """If set, invite applies only to this client card (must belong to current master)."""
    replace: bool = False
    """If true, revoke other pending invites for the same client before creating a new one."""


class InvitationOut(BaseModel):
    token: str
    expires_at: datetime
    target_email: EmailStr | None
    target_client_id: UUID | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


class InvitationPublicOut(BaseModel):
    master_display_name: str
    timezone: str
    token: str
    expires_at: datetime


class InvitationLandingResponse(BaseModel):
    master_display_name: str
    timezone: str
    token: str
    expires_at: datetime
    accepted_at: datetime | None
    linked_client_id: UUID | None
    services: list[ServiceSchema]
    invite_kind: Literal["open", "client"] = "open"
    master_record_has_email: bool = False


class InvitationAcceptOut(BaseModel):
    client_id: UUID
    email_mismatch_with_master_record: bool = False


class InvitationAccept(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
