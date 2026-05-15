"""Invitation flows."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.service import ServiceOut


class InvitationCreate(BaseModel):
    expires_hours: int = Field(default=72, ge=1, le=24 * 30)
    target_email: EmailStr | None = None


class InvitationOut(BaseModel):
    model_config = {"from_attributes": True}

    token: str
    expires_at: datetime
    target_email: EmailStr | None


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
    services: list[ServiceOut]


class InvitationAcceptOut(BaseModel):
    client_id: UUID


class InvitationAccept(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
