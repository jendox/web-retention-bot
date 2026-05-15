from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ClientCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None


class ClientSchema(BaseModel):
    id: UUID
    display_name: str
    phone: str | None
    email: EmailStr | None

    model_config = ConfigDict(
        from_attributes=True,
    )


class ClientUpdate(BaseModel):
    """Частичное обновление карточки клиента и связи мастер–клиент."""

    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    notes: str | None = Field(default=None, max_length=2000)
    alias: str | None = Field(default=None, max_length=200)

    @field_validator('phone', mode='before')
    @classmethod
    def empty_phone_to_none(cls, v: str | None) -> str | None:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return v

    @field_validator('email', mode='before')
    @classmethod
    def empty_email_to_none(cls, v: str | None) -> str | None:
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return v


class MasterClientOut(BaseModel):
    id: UUID
    alias: str | None
    notes: str | None
    invitation_status: str

    model_config = ConfigDict(
        from_attributes=True,
    )


class ClientWithLinkResponse(BaseModel):
    """Одна связка «клиент + привязка мастера» — как в списке и при создании."""

    client: ClientSchema
    link: MasterClientOut
