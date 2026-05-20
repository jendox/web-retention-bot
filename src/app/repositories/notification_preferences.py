from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.notifications import DeliveryChannel, NotificationEventType, PreferenceCategory
from app.models.notifications.models import NotificationChannel, UserNotificationPreference
from app.repositories.base import BaseRepository
from app.services.notifications.settings_catalog import (
    CHANNEL_DEFS,
    CabinetKind,
    NotificationTopicDef,
    topics_for_cabinet,
)

__all__ = ["NotificationPreferenceRepository", "get_notification_preference_repo"]


class NotificationPreferenceRepository(BaseRepository):

    async def list_preferences(self, user_id: UUID) -> list[UserNotificationPreference]:
        stmt = select(UserNotificationPreference).where(UserNotificationPreference.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def list_channels(self, user_id: UUID) -> list[NotificationChannel]:
        stmt = select(NotificationChannel).where(NotificationChannel.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def get_channel(self, user_id: UUID, kind: DeliveryChannel) -> NotificationChannel | None:
        stmt = (
            select(NotificationChannel)
            .where(
                NotificationChannel.user_id == user_id,
                NotificationChannel.kind == kind,
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_channel(
        self,
        *,
        user_id: UUID,
        kind: DeliveryChannel,
        address: str,
        is_verified: bool = True,
    ) -> NotificationChannel:
        existing = await self.get_channel(user_id, kind)
        if existing is not None:
            existing.address = address
            existing.is_verified = is_verified
            await self.session.flush()
            return existing

        channel = NotificationChannel(
            user_id=user_id,
            kind=kind,
            address=address,
            is_verified=is_verified,
        )
        self.session.add(channel)
        await self.session.flush()
        return channel

    async def delete_channel(self, user_id: UUID, kind: DeliveryChannel) -> None:
        stmt = delete(NotificationChannel).where(
            NotificationChannel.user_id == user_id,
            NotificationChannel.kind == kind,
        )
        await self.session.execute(stmt)

    async def ensure_defaults(self, user_id: UUID, *, cabinet: CabinetKind) -> None:
        for topic in topics_for_cabinet(cabinet):
            for channel_def in CHANNEL_DEFS:
                if not channel_def.available or channel_def.kind != DeliveryChannel.EMAIL:
                    continue
                stmt = select(UserNotificationPreference).where(
                    UserNotificationPreference.user_id == user_id,
                    UserNotificationPreference.channel == channel_def.kind,
                )
                if topic.event_type is not None:
                    stmt = stmt.where(UserNotificationPreference.event_type == topic.event_type)
                else:
                    stmt = stmt.where(UserNotificationPreference.event_type.is_(None))
                result = await self.session.execute(stmt)
                if result.scalar_one_or_none() is not None:
                    continue
                await self._upsert_pref(
                    user_id=user_id,
                    channel=channel_def.kind,
                    enabled=True,
                    category=topic.category,
                    event_type=topic.event_type,
                )

    async def set_topic_channel(
        self,
        *,
        user_id: UUID,
        topic: NotificationTopicDef,
        channel: DeliveryChannel,
        enabled: bool,
    ) -> None:
        await self._upsert_pref(
            user_id=user_id,
            channel=channel,
            enabled=enabled,
            category=topic.category,
            event_type=topic.event_type,
        )

    async def is_channel_enabled_for_event(
        self,
        user_id: UUID,
        channel: DeliveryChannel,
        event_type: NotificationEventType,
        *,
        category: PreferenceCategory | None,
    ) -> bool:
        if channel == DeliveryChannel.IN_APP:
            return True

        matchers = [UserNotificationPreference.event_type == event_type]
        if category is not None:
            matchers.append(
                and_(
                    UserNotificationPreference.event_type.is_(None),
                    UserNotificationPreference.category == category,
                ),
            )
        stmt = select(UserNotificationPreference.enabled).where(
            UserNotificationPreference.user_id == user_id,
            UserNotificationPreference.channel == channel,
            or_(*matchers),
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if row is None:
            return channel == DeliveryChannel.EMAIL
        return bool(row[0])

    async def _upsert_pref(
        self,
        *,
        user_id: UUID,
        channel: DeliveryChannel,
        enabled: bool,
        category: PreferenceCategory | None,
        event_type: NotificationEventType | None,
    ) -> UserNotificationPreference:
        stmt = select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == user_id,
            UserNotificationPreference.channel == channel,
        )
        if event_type is not None:
            stmt = stmt.where(UserNotificationPreference.event_type == event_type)
        else:
            stmt = stmt.where(UserNotificationPreference.event_type.is_(None))
        result = await self.session.execute(stmt)
        pref = result.scalar_one_or_none()

        if pref is None:
            pref = UserNotificationPreference(
                user_id=user_id,
                channel=channel,
                category=category,
                event_type=event_type,
                enabled=enabled,
            )
            self.session.add(pref)
        else:
            pref.enabled = enabled
            pref.category = category

        await self.session.flush()
        return pref


def get_notification_preference_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotificationPreferenceRepository:
    return NotificationPreferenceRepository(session)
