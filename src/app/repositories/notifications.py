from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.models import NotificationDelivery, NotificationEvent, UserNotification
from app.models.notifications import DeliveryChannel, DeliveryStatus, NotificationEventType
from app.repositories.base import BaseRepository


@dataclass
class NotificationEventCreate:
    type: NotificationEventType
    payload: dict[str, str]
    occurred_at: datetime | None = None
    target_user_id: UUID | None = None
    actor_user_id: UUID | None = None
    master_profile_id: UUID | None = None
    client_id: UUID | None = None
    booking_id: UUID | None = None


@dataclass
class UserNotificationCreate:
    dedup_key: str
    event_type: NotificationEventType
    title: str
    body: str
    event_id: UUID | None = None
    recipient_user_id: UUID | None = None
    recipient_client_id: UUID | None = None
    payload: dict[str, str] | None = None
    link_url: str | None = None


@dataclass
class NotificationDeliveryCreate:
    user_notification_id: UUID
    channel: DeliveryChannel
    status: DeliveryStatus
    scheduled_at: datetime
    notification_channel_id: UUID | None = None


class NotificationEventRepository(BaseRepository):

    async def create(self, event: NotificationEventCreate) -> NotificationEvent:
        if event.occurred_at is None:
            event.occurred_at = datetime.now(UTC)

        event_entity = NotificationEvent(**asdict(event))
        self.session.add(event_entity)
        await self.session.flush()
        return event_entity


class UserNotificationRepository(BaseRepository):

    async def create(self, notification: UserNotificationCreate) -> UserNotification:
        notification_entity = UserNotification(**asdict(notification))
        self.session.add(notification_entity)
        await self.session.flush()
        return notification_entity


class NotificationDeliveryRepository(BaseRepository):

    async def create(self, delivery: NotificationDeliveryCreate) -> NotificationDelivery:
        deliver_entity = NotificationDelivery(**asdict(delivery))
        self.session.add(deliver_entity)
        await self.session.flush()
        return deliver_entity

    async def get(self, delivery_id: UUID) -> NotificationDelivery | None:
        stmt = (
            select(NotificationDelivery)
            .where(NotificationDelivery.id == delivery_id)
            .options(selectinload(NotificationDelivery.user_notification))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


def get_notification_event_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationEventRepository:
    return NotificationEventRepository(session)


def get_user_notification_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserNotificationRepository:
    return UserNotificationRepository(session)


def get_notification_delivery_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationDeliveryRepository:
    return NotificationDeliveryRepository(session)
