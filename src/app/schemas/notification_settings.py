from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class InAppChannelOut(BaseModel):
    available: bool = True
    connected: bool = True
    label: str = "В приложении"
    description: str = "Колокольчик в кабинете — всегда включён."


class ExternalChannelOut(BaseModel):
    kind: str
    label: str
    description: str
    available: bool
    connectable: bool
    connected: bool
    address: str | None = None
    #: Deep link to messenger bot (t.me/...?start=token) while link is pending.
    connect_url: str | None = None
    coming_soon_label: str | None = None


class TopicChannelPrefsOut(BaseModel):
    email: bool = False
    telegram: bool = False
    sms: bool = False


class NotificationTopicOut(BaseModel):
    id: str
    label: str
    description: str
    channels: TopicChannelPrefsOut


class NotificationSettingsOut(BaseModel):
    in_app: InAppChannelOut
    channels: list[ExternalChannelOut]
    topics: list[NotificationTopicOut]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "in_app": {
                        "available": True,
                        "connected": True,
                        "label": "В приложении",
                        "description": "Колокольчик в кабинете — всегда включён.",
                    },
                    "channels": [
                        {
                            "kind": "email",
                            "label": "Email",
                            "description": "Письма на адрес аккаунта.",
                            "available": True,
                            "connectable": False,
                            "connected": True,
                            "address": "client@example.com",
                            "connect_url": None,
                            "coming_soon_label": None,
                        },
                        {
                            "kind": "telegram",
                            "label": "Telegram",
                            "description": "Уведомления в Telegram-боте.",
                            "available": True,
                            "connectable": True,
                            "connected": False,
                            "address": None,
                            "connect_url": "https://t.me/retention_studio_bot?start=abc123token",
                            "coming_soon_label": None,
                        },
                    ],
                    "topics": [
                        {
                            "id": "booking_updates",
                            "label": "Записи",
                            "description": "Создание, переносы и отмены записей.",
                            "channels": {"email": True, "telegram": False, "sms": False},
                        },
                    ],
                },
            ],
        },
    )


class TopicChannelPrefsPatch(BaseModel):
    email: bool | None = None
    telegram: bool | None = None
    sms: bool | None = None


class NotificationTopicPatch(BaseModel):
    id: str
    channels: TopicChannelPrefsPatch


class NotificationSettingsPatch(BaseModel):
    topics: list[NotificationTopicPatch] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "topics": [
                        {
                            "id": "booking_updates",
                            "channels": {"email": True, "telegram": True},
                        },
                    ],
                },
            ],
        },
    )


class LinkNotificationChannelIn(BaseModel):
    #: Legacy/mock; bot channels use deep link + /start token instead of manual address.
    address: str | None = Field(default=None, max_length=512)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {},
            ],
        },
    )
