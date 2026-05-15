from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


@dataclass(frozen=True)
class PasswordValidationResult:
    ok: bool
    errors: tuple[str, ...]

    @classmethod
    def success(cls) -> Self:
        return cls(ok=True, errors=())

    @classmethod
    def failure(cls, *errors: str) -> Self:
        return cls(ok=False, errors=tuple(errors))


def validate_password(password: str) -> PasswordValidationResult:
    errors: list[str] = []

    if password is None:
        return PasswordValidationResult.failure("Пароль обязателен.")

    normalized = password.strip()
    if not normalized:
        return PasswordValidationResult.failure("Пароль не может быть пустым.")

    if len(normalized) < MIN_PASSWORD_LENGTH:
        errors.append(f"Пароль должен быть не менее {MIN_PASSWORD_LENGTH} символов.")
    if len(normalized) > MAX_PASSWORD_LENGTH:
        errors.append(f"Пароль должен быть не более {MAX_PASSWORD_LENGTH} символов.")

    if not any(ch.isalpha() for ch in normalized):
        errors.append("Пароль должен содержать хотя бы одну букву.")
    if not any(ch.isdigit() for ch in normalized):
        errors.append("Пароль должен содержать хотя бы одну цифру.")

    if errors:
        return PasswordValidationResult.failure(*errors)
    return PasswordValidationResult.success()


class RegisterPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    master_display_name: str = Field(min_length=2, max_length=200)

    @field_validator("password", mode="before")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        result = validate_password(password=value)
        if not result.ok:
            raise ValueError("; ".join(result.errors))
        return value


class RegisterClientPayload(BaseModel):
    """Регистрация клиента без профиля мастера (по инвайт-ссылке)."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password", mode="before")
    @classmethod
    def _validate_client_password(cls, value: str) -> str:
        result = validate_password(password=value)
        if not result.ok:
            raise ValueError("; ".join(result.errors))
        return value


class RegisterAcceptedOut(BaseModel):
    """Successful registration: user + master row created; session only after verify-email."""

    id: UUID
    email: EmailStr
    email_verified: Literal[False] = False

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "email": "user@example.com",
                    "email_verified": False,
                },
            ],
        },
    )


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailPayload(BaseModel):
    token: str = Field(min_length=16)
