from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimeStampedModel
from app.models.notifications.enums import (
    DeliveryChannel,
    DeliveryStatus,
    NotificationEventType,
    PreferenceCategory,
    ScheduledNotificationPurpose,
    ScheduledNotificationStatus,
)
from app.models.user import User


class NotificationEvent(Base):
    __tablename__ = "notification_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    type: Mapped[NotificationEventType] = mapped_column(
        SAEnum(
            NotificationEventType,
            values_callable=lambda o: [e.value for e in o],
            native_enum=False,
            length=64,
        ),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    master_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("master_profiles.id"), nullable=True, index=True,
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("clients.id"), nullable=True, index=True,
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("bookings.id"), nullable=True, index=True,
    )

    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    user_notifications: Mapped[list[UserNotification]] = relationship(
        "UserNotification", back_populates="event",
    )


class UserNotification(TimeStampedModel):
    __tablename__ = "user_notifications"
    __table_args__ = (
        UniqueConstraint("dedup_key", name="uq_user_notifications_dedup_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("notification_events.id"), nullable=True, index=True,
    )
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True,
    )
    recipient_client_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("clients.id"), nullable=True, index=True,
    )

    event_type: Mapped[NotificationEventType] = mapped_column(
        SAEnum(
            NotificationEventType,
            values_callable=lambda o: [e.value for e in o],
            native_enum=False,
            length=64,
        ),
        nullable=False,
        default=NotificationEventType.DEFAULT,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    link_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dedup_key: Mapped[str] = mapped_column(String(512), nullable=False)

    event: Mapped[NotificationEvent | None] = relationship(
        "NotificationEvent", back_populates="user_notifications",
    )
    deliveries: Mapped[list[NotificationDelivery]] = relationship(
        "NotificationDelivery", back_populates="user_notification", cascade="all, delete-orphan",
    )


class NotificationDelivery(TimeStampedModel):
    __tablename__ = "notification_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_notification_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_notifications.id", ondelete="CASCADE"), nullable=False,
    )

    channel: Mapped[DeliveryChannel] = mapped_column(
        SAEnum(
            DeliveryChannel,
            values_callable=lambda o: [e.value for e in o],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        index=True,
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        SAEnum(
            DeliveryStatus,
            values_callable=lambda o: [e.value for e in o],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=DeliveryStatus.PENDING,
        index=True,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(512), nullable=True)

    notification_channel_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("notification_channels.id"), nullable=True,
    )

    user_notification: Mapped[UserNotification] = relationship(
        "UserNotification", back_populates="deliveries",
    )


class UserNotificationPreference(TimeStampedModel):
    __tablename__ = "user_notification_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "channel",
            "event_type",
            name="uq_prefs_user_channel_event_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )

    channel: Mapped[DeliveryChannel] = mapped_column(
        SAEnum(
            DeliveryChannel,
            values_callable=lambda o: [e.value for e in o],
            native_enum=False,
            length=32,
        ),
        nullable=False,
    )
    event_type: Mapped[NotificationEventType | None] = mapped_column(
        SAEnum(
            NotificationEventType,
            values_callable=lambda o: [e.value for e in o],
            native_enum=False,
            length=64,
        ),
        nullable=True,
    )
    category: Mapped[PreferenceCategory | None] = mapped_column(
        SAEnum(
            PreferenceCategory,
            values_callable=lambda o: [e.value for e in o],
            native_enum=False,
            length=32,
        ),
        nullable=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ScheduledNotification(Base):
    __tablename__ = "scheduled_notifications"
    __table_args__ = (
        UniqueConstraint("booking_id", "purpose", name="uq_scheduled_booking_purpose"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    purpose: Mapped[ScheduledNotificationPurpose] = mapped_column(
        SAEnum(
            ScheduledNotificationPurpose,
            values_callable=lambda o: [e.value for e in o],
            native_enum=False,
            length=32,
        ),
        nullable=False,
    )
    fire_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    status: Mapped[ScheduledNotificationStatus] = mapped_column(
        SAEnum(
            ScheduledNotificationStatus,
            values_callable=lambda o: [e.value for e in o],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=ScheduledNotificationStatus.PENDING,
        index=True,
    )

    user_notification_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_notifications.id", ondelete="SET NULL"), nullable=True,
    )

    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    recipient_client_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("clients.id"), nullable=True,
    )


class RetentionPolicy(Base):
    __tablename__ = "retention_policies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    idle_days: Mapped[int] = mapped_column(nullable=False)
    target_audience: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[NotificationEventType] = mapped_column(
        SAEnum(
            NotificationEventType,
            values_callable=lambda o: [e.value for e in o],
            native_enum=False,
            length=64,
        ),
        nullable=False,
        default=NotificationEventType.REENGAGEMENT_IDLE,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    kind: Mapped[DeliveryChannel] = mapped_column(
        SAEnum(
            DeliveryChannel,
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
            length=32,
        ),
    )
    address: Mapped[str] = mapped_column(String(512))
    is_verified: Mapped[bool] = mapped_column(default=False)

    user: Mapped[User | None] = relationship("User")
