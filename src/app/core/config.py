from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class InfraSettings(BaseModel):
    database_url: str = Field(default="postgresql+asyncpg://retention:retention@localhost:5432/retention")
    redis_url: str = Field(default="redis://localhost:6379/0")


class SecuritySettings(BaseModel):
    #: HMAC signing for email verification tokens and other auth material.
    secret_key: str = Field(default="development-secret-change-me")
    email_verification_ttl_seconds: int = Field(default=60 * 60 * 72)
    #: Browser origin used in verification emails (SPA opens /verify-email?token=...).
    frontend_public_origin: str = Field(default="http://localhost:5173")
    #: When True (default dev), verification URL is emitted to logs (in addition to SMTP if enabled).
    auth_log_verification_link: bool = Field(default=True)


class SessionSettings(BaseModel):
    cookie_name: str = "session_id"
    cookie_secure: bool = False
    ttl_seconds: int = 60 * 60 * 24 * 14


class CelerySettings(BaseModel):
    broker_url: str
    result_backend: str
    task_always_eager: bool = False
    task_eager_propagates: bool = False


class NotificationSettings(BaseModel):
    #: When True, mark email deliveries sent in-process (no Celery); useful for tests and local dev.
    eager_deliveries: bool = Field(default=False)


class SmtpSettings(BaseModel):
    #: When False, verification emails are only logged (see SECURITY__AUTH_LOG_VERIFICATION_LINK); no TCP to SMTP.
    enabled: bool = Field(default=True)
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=25)
    #: Implicit TLS (SMTPS), typically port 465.
    tls: bool = Field(default=False)
    #: STARTTLS after connect, typically port 587.
    start_tls: bool = Field(default=False)
    username: str | None = Field(default=None)
    password: str | None = Field(default=None)
    from_email: str = Field(default="noreply@localhost")


class Settings(BaseSettings):
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"
    AVAILABILITY_SLOT_STEP_MINUTES: int = 15

    infra: InfraSettings = Field(default_factory=InfraSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    session: SessionSettings = Field(default_factory=SessionSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    smtp: SmtpSettings = Field(default_factory=SmtpSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
