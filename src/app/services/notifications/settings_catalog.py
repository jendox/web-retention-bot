from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.models.notifications import DeliveryChannel, NotificationEventType, PreferenceCategory

type CabinetKind = Literal["client", "master"]


@dataclass(frozen=True)
class NotificationTopicDef:
    id: str
    label: str
    description: str
    category: PreferenceCategory | None = None
    event_type: NotificationEventType | None = None


@dataclass(frozen=True)
class ChannelDef:
    kind: DeliveryChannel
    label: str
    description: str
    connectable: bool
    available: bool = True
    coming_soon_label: str | None = None


CLIENT_TOPICS: tuple[NotificationTopicDef, ...] = (
    NotificationTopicDef(
        id="booking_events",
        label="Записи",
        description="Создание, перенос и отмена визитов.",
        category=PreferenceCategory.BOOKING,
    ),
    NotificationTopicDef(
        id="visit_reminders",
        label="Напоминания перед визитом",
        description="Напоминания о предстоящих записях.",
        event_type=NotificationEventType.REMINDER_BEFORE_VISIT,
    ),
)

MASTER_TOPICS: tuple[NotificationTopicDef, ...] = (
    NotificationTopicDef(
        id="booking_events",
        label="Действия с записями",
        description="Запись, перенос и отмена через кабинет клиента.",
        category=PreferenceCategory.BOOKING,
    ),
    NotificationTopicDef(
        id="studio_system",
        label="Служебные сообщения",
        description="Приглашения и важные изменения в аккаунте студии.",
        category=PreferenceCategory.SYSTEM,
        event_type=NotificationEventType.DEFAULT,
    ),
)

CHANNEL_DEFS: tuple[ChannelDef, ...] = (
    ChannelDef(
        kind=DeliveryChannel.EMAIL,
        label="Email",
        description="Письма на адрес входа в аккаунт.",
        connectable=False,
    ),
    ChannelDef(
        kind=DeliveryChannel.TELEGRAM,
        label="Telegram",
        description="Уведомления через бота @retention_studio_bot — нажмите «Подключить» и Start в чате.",
        connectable=True,
    ),
    ChannelDef(
        kind=DeliveryChannel.SMS,
        label="SMS",
        description="Сообщения на номер телефона.",
        connectable=True,
        available=False,
        coming_soon_label="Скоро",
    ),
)

BOT_LINKABLE_CHANNELS = frozenset({DeliveryChannel.TELEGRAM})


def topics_for_cabinet(cabinet: CabinetKind) -> tuple[NotificationTopicDef, ...]:
    return CLIENT_TOPICS if cabinet == "client" else MASTER_TOPICS


def category_for_event_type(event_type: NotificationEventType) -> PreferenceCategory | None:
    if event_type in {
        NotificationEventType.BOOKING_CREATED,
        NotificationEventType.BOOKING_CANCELLED,
        NotificationEventType.BOOKING_MOVED,
    }:
        return PreferenceCategory.BOOKING
    if event_type in {NotificationEventType.EMAIL_VERIFICATION, NotificationEventType.DEFAULT}:
        return PreferenceCategory.SYSTEM
    if event_type == NotificationEventType.REMINDER_BEFORE_VISIT:
        return PreferenceCategory.RETENTION
    return None
