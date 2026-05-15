"""Client representations."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ClientCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None


class ClientOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    display_name: str
    phone: str | None
    email: EmailStr | None


class MasterClientOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    alias: str | None
    notes: str | None
    invitation_status: str
