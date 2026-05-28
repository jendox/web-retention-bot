from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.models import NotificationDelivery, NotificationEvent, ScheduledNotification, UserNotification
from app.models.notifications import (
    DeliveryChannel,
    DeliveryStatus,
    NotificationEventType,
    ScheduledNotificationPurpose,
    ScheduledNotificationStatus,
)
from app.repositories.base import BaseRepository
from app.repositories.notification_cabinet import (
    notification_belongs_to_client_cabinet,
    notification_belongs_to_master_cabinet,
)


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


@dataclass(frozen=True)
class ScheduledNotificationCreate:
    booking_id: UUID
    purpose: ScheduledNotificationPurpose
    fire_at: datetime
    recipient_user_id: UUID | None = None
    recipient_client_id: UUID | None = None


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

    def _for_user(self, user_id: UUID, *, cabinet_filter):
        return [
            UserNotification.recipient_user_id == user_id,
            cabinet_filter(),
        ]

    async def count_for_client_cabinet(self, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(UserNotification)
            .where(*self._for_user(user_id, cabinet_filter=notification_belongs_to_client_cabinet))
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def list_for_client_cabinet_page(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[UserNotification]:
        stmt = (
            select(UserNotification)
            .where(*self._for_user(user_id, cabinet_filter=notification_belongs_to_client_cabinet))
            .order_by(UserNotification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = await self.session.execute(stmt)
        return list(rows.scalars())

    async def count_unread_for_client_cabinet(self, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(UserNotification).where(
            *self._for_user(user_id, cabinet_filter=notification_belongs_to_client_cabinet),
            UserNotification.read_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def count_for_master_cabinet(self, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(UserNotification)
            .where(*self._for_user(user_id, cabinet_filter=notification_belongs_to_master_cabinet))
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def list_for_master_cabinet_page(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[UserNotification]:
        stmt = (
            select(UserNotification)
            .where(*self._for_user(user_id, cabinet_filter=notification_belongs_to_master_cabinet))
            .order_by(UserNotification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = await self.session.execute(stmt)
        return list(rows.scalars())

    async def count_unread_for_master_cabinet(self, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(UserNotification).where(
            *self._for_user(user_id, cabinet_filter=notification_belongs_to_master_cabinet),
            UserNotification.read_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_for_user(self, notification_id: UUID, user_id: UUID) -> UserNotification | None:
        stmt = (
            select(UserNotification)
            .where(
                UserNotification.id == notification_id,
                UserNotification.recipient_user_id == user_id,
            )
            .limit(1)
        )
        row = await self.session.execute(stmt)
        return row.scalar_one_or_none()


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


class ScheduledNotificationRepository(BaseRepository):
    async def upsert(self, payload: ScheduledNotificationCreate) -> ScheduledNotification:
        stmt = insert(ScheduledNotification).values(
            booking_id=payload.booking_id,
            purpose=payload.purpose,
            fire_at=payload.fire_at,
            status=ScheduledNotificationStatus.PENDING,
            recipient_user_id=payload.recipient_user_id,
            recipient_client_id=payload.recipient_client_id,
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=[
                ScheduledNotification.booking_id,
                ScheduledNotification.purpose,
            ],
            set_={
                "fire_at": stmt.excluded.fire_at,
                "status": stmt.excluded.status,
                "user_notification_id": None,
                "recipient_user_id": stmt.excluded.recipient_user_id,
                "recipient_client_id": stmt.excluded.recipient_client_id,
            },
        ).returning(ScheduledNotification)

        result = await self.session.execute(stmt)

        return result.scalar_one()

    async def cancel_pending_for_booking(self, booking_id: UUID) -> int:
        stmt = (
            update(ScheduledNotification)
            .where(
                ScheduledNotification.booking_id == booking_id,
                ScheduledNotification.status == ScheduledNotificationStatus.PENDING,
            )
            .values(status=ScheduledNotificationStatus.CANCELLED)
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0

    async def claim_due(self, *, now: datetime, limit: int) -> list[ScheduledNotification]:
        subquery = (
            select(ScheduledNotification.id)
            .where(
                ScheduledNotification.status == ScheduledNotificationStatus.PENDING,
                ScheduledNotification.fire_at <= now,
            )
            .order_by(ScheduledNotification.fire_at.asc(), ScheduledNotification.id.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
            .subquery()
        )
        stmt = (
            update(ScheduledNotification)
            .where(ScheduledNotification.id.in_(select(subquery.c.id)))
            .values(status=ScheduledNotificationStatus.CLAIMED)
            .returning(ScheduledNotification)
        )

        result = await self.session.execute(stmt)
        return sorted(result.scalars(), key=lambda item: (item.fire_at, item.id))

    async def mark_done(
        self,
        scheduled_notification_id: UUID,
        *,
        user_notification_id: UUID | None = None,
    ) -> ScheduledNotification | None:
        stmt = (
            update(ScheduledNotification)
            .where(
                ScheduledNotification.id == scheduled_notification_id,
                ScheduledNotification.status == ScheduledNotificationStatus.CLAIMED,
            )
            .values(
                status=ScheduledNotificationStatus.DONE,
                user_notification_id=user_notification_id,
            )
            .returning(ScheduledNotification)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def release_claimed(self, scheduled_notification_id: UUID) -> ScheduledNotification | None:
        stmt = (
            update(ScheduledNotification)
            .where(
                ScheduledNotification.id == scheduled_notification_id,
                ScheduledNotification.status == ScheduledNotificationStatus.CLAIMED,
            )
            .values(status=ScheduledNotificationStatus.PENDING)
            .returning(ScheduledNotification)
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


def get_scheduled_notification_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ScheduledNotificationRepository:
    return ScheduledNotificationRepository(session)
