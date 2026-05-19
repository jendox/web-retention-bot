"""initial schema

Revision ID: 20260519_initial
Revises:
Create Date: 2026-05-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260519_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


notification_event_type = sa.Enum(
    "default",
    "booking_created",
    "booking_moved",
    "booking_cancelled",
    "reminder_before_visit",
    "reengagement_idle",
    "email_verification",
    name="notificationeventtype",
    native_enum=False,
    length=64,
)
delivery_channel = sa.Enum("in_app", "email", "telegram", "viber", "sms", name="deliverychannel", native_enum=False, length=32)


def upgrade() -> None:
    op.create_table(
        "retention_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("idle_days", sa.Integer(), nullable=False),
        sa.Column("target_audience", sa.String(length=64), nullable=False),
        sa.Column("event_type", notification_event_type, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "clients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clients_user_id"), "clients", ["user_id"], unique=False)

    op.create_table(
        "master_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("public_slug", sa.String(length=80), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("default_currency", sa.Enum("USD", "EUR", "BYN", "RUB", name="currency", native_enum=False, length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_master_profiles_public_slug"), "master_profiles", ["public_slug"], unique=False)

    op.create_table(
        "notification_channels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("kind", delivery_channel, nullable=False),
        sa.Column("address", sa.String(length=512), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_notification_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("channel", delivery_channel, nullable=False),
        sa.Column("event_type", notification_event_type, nullable=True),
        sa.Column(
            "category",
            sa.Enum("booking", "marketing", "retention", "system", name="preferencecategory", native_enum=False, length=32),
            nullable=True,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "channel", "event_type", name="uq_prefs_user_channel_event_type"),
    )
    op.create_index(op.f("ix_user_notification_preferences_user_id"), "user_notification_preferences", ["user_id"], unique=False)

    op.create_table(
        "invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("master_id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("target_email", sa.String(length=320), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("linked_client_id", sa.Uuid(), nullable=True),
        sa.Column("target_client_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["linked_client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["master_id"], ["master_profiles.id"]),
        sa.ForeignKeyConstraint(["target_client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invitations_target_client_id"), "invitations", ["target_client_id"], unique=False)
    op.create_index(op.f("ix_invitations_token"), "invitations", ["token"], unique=True)

    op.create_table(
        "master_clients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("master_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("alias", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("linked_account_email", sa.String(length=320), nullable=True),
        sa.Column("invite_email_mismatch", sa.Boolean(), nullable=False),
        sa.Column("invitation_status", sa.Enum("PENDING", "LINKED", "REVOKED", name="invitationstatus", native_enum=False, length=32), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["master_id"], ["master_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "services",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("master_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.Enum("USD", "EUR", "BYN", "RUB", name="currency", native_enum=False, length=3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["master_id"], ["master_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "weekly_schedule_days",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("master_id", sa.Uuid(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_weekly_schedule_day_weekday_range"),
        sa.ForeignKeyConstraint(["master_id"], ["master_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("master_id", "weekday", name="uq_weekly_schedule_day"),
    )
    op.create_index("ix_weekly_schedule_days_master_weekday", "weekly_schedule_days", ["master_id", "weekday"], unique=False)
    op.create_table(
        "schedule_date_overrides",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("master_id", sa.Uuid(), nullable=False),
        sa.Column("schedule_date", sa.Date(), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["master_id"], ["master_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("master_id", "schedule_date", name="uq_schedule_date_override"),
    )
    op.create_table(
        "weekly_schedule_intervals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("day_id", sa.Uuid(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("start_time < end_time", name="ck_weekly_schedule_interval_time_order"),
        sa.ForeignKeyConstraint(["day_id"], ["weekly_schedule_days.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("day_id", "start_time", name="uq_weekly_schedule_interval_start"),
    )
    op.create_index("ix_weekly_schedule_interval_day_order", "weekly_schedule_intervals", ["day_id", "sort_order"], unique=False)
    op.create_table(
        "schedule_date_override_intervals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("override_id", sa.Uuid(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("start_time < end_time", name="ck_schedule_date_override_interval_time_order"),
        sa.ForeignKeyConstraint(["override_id"], ["schedule_date_overrides.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("override_id", "start_time", name="uq_schedule_date_override_interval_start"),
    )
    op.create_index("ix_schedule_date_override_intervals_order", "schedule_date_override_intervals", ["override_id", "sort_order"], unique=False)

    op.create_table(
        "bookings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("master_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("price_snapshot", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency_snapshot", sa.String(length=3), nullable=False),
        sa.Column("status", sa.Enum("scheduled", "cancelled", name="bookingstatus", native_enum=False, length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["master_id"], ["master_profiles.id"]),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "notification_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type", notification_event_type, nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("target_user_id", sa.Uuid(), nullable=True),
        sa.Column("master_profile_id", sa.Uuid(), nullable=True),
        sa.Column("client_id", sa.Uuid(), nullable=True),
        sa.Column("booking_id", sa.Uuid(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["master_profile_id"], ["master_profiles.id"]),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_events_booking_id"), "notification_events", ["booking_id"], unique=False)
    op.create_index(op.f("ix_notification_events_client_id"), "notification_events", ["client_id"], unique=False)
    op.create_index(op.f("ix_notification_events_master_profile_id"), "notification_events", ["master_profile_id"], unique=False)
    op.create_index(op.f("ix_notification_events_occurred_at"), "notification_events", ["occurred_at"], unique=False)
    op.create_index(op.f("ix_notification_events_type"), "notification_events", ["type"], unique=False)

    op.create_table(
        "user_notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=True),
        sa.Column("recipient_client_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", notification_event_type, nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("link_url", sa.String(length=2048), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedup_key", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["notification_events.id"]),
        sa.ForeignKeyConstraint(["recipient_client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_key", name="uq_user_notifications_dedup_key"),
    )
    op.create_index(op.f("ix_user_notifications_event_id"), "user_notifications", ["event_id"], unique=False)
    op.create_index(op.f("ix_user_notifications_recipient_client_id"), "user_notifications", ["recipient_client_id"], unique=False)
    op.create_index(op.f("ix_user_notifications_recipient_user_id"), "user_notifications", ["recipient_user_id"], unique=False)
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_notification_id", sa.Uuid(), nullable=False),
        sa.Column("channel", delivery_channel, nullable=False),
        sa.Column("status", sa.Enum("pending", "sending", "sent", "failed", "skipped", "cancelled", name="deliverystatus", native_enum=False, length=32), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(length=512), nullable=True),
        sa.Column("notification_channel_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["notification_channel_id"], ["notification_channels.id"]),
        sa.ForeignKeyConstraint(["user_notification_id"], ["user_notifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_deliveries_channel"), "notification_deliveries", ["channel"], unique=False)
    op.create_index(op.f("ix_notification_deliveries_scheduled_at"), "notification_deliveries", ["scheduled_at"], unique=False)
    op.create_index(op.f("ix_notification_deliveries_status"), "notification_deliveries", ["status"], unique=False)
    op.create_table(
        "scheduled_notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.Enum("reminder_24h", "reminder_1h", name="schedulednotificationpurpose", native_enum=False, length=32), nullable=False),
        sa.Column("fire_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Enum("pending", "claimed", "done", "cancelled", name="schedulednotificationstatus", native_enum=False, length=32), nullable=False),
        sa.Column("user_notification_id", sa.Uuid(), nullable=True),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=True),
        sa.Column("recipient_client_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_notification_id"], ["user_notifications.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id", "purpose", name="uq_scheduled_booking_purpose"),
    )
    op.create_index(op.f("ix_scheduled_notifications_booking_id"), "scheduled_notifications", ["booking_id"], unique=False)
    op.create_index(op.f("ix_scheduled_notifications_fire_at"), "scheduled_notifications", ["fire_at"], unique=False)
    op.create_index(op.f("ix_scheduled_notifications_status"), "scheduled_notifications", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_scheduled_notifications_status"), table_name="scheduled_notifications")
    op.drop_index(op.f("ix_scheduled_notifications_fire_at"), table_name="scheduled_notifications")
    op.drop_index(op.f("ix_scheduled_notifications_booking_id"), table_name="scheduled_notifications")
    op.drop_table("scheduled_notifications")
    op.drop_index(op.f("ix_notification_deliveries_status"), table_name="notification_deliveries")
    op.drop_index(op.f("ix_notification_deliveries_scheduled_at"), table_name="notification_deliveries")
    op.drop_index(op.f("ix_notification_deliveries_channel"), table_name="notification_deliveries")
    op.drop_table("notification_deliveries")
    op.drop_index(op.f("ix_user_notifications_recipient_user_id"), table_name="user_notifications")
    op.drop_index(op.f("ix_user_notifications_recipient_client_id"), table_name="user_notifications")
    op.drop_index(op.f("ix_user_notifications_event_id"), table_name="user_notifications")
    op.drop_table("user_notifications")
    op.drop_index(op.f("ix_notification_events_type"), table_name="notification_events")
    op.drop_index(op.f("ix_notification_events_occurred_at"), table_name="notification_events")
    op.drop_index(op.f("ix_notification_events_master_profile_id"), table_name="notification_events")
    op.drop_index(op.f("ix_notification_events_client_id"), table_name="notification_events")
    op.drop_index(op.f("ix_notification_events_booking_id"), table_name="notification_events")
    op.drop_table("notification_events")
    op.drop_table("bookings")
    op.drop_index("ix_schedule_date_override_intervals_order", table_name="schedule_date_override_intervals")
    op.drop_table("schedule_date_override_intervals")
    op.drop_index("ix_weekly_schedule_interval_day_order", table_name="weekly_schedule_intervals")
    op.drop_table("weekly_schedule_intervals")
    op.drop_table("schedule_date_overrides")
    op.drop_index("ix_weekly_schedule_days_master_weekday", table_name="weekly_schedule_days")
    op.drop_table("weekly_schedule_days")
    op.drop_table("services")
    op.drop_table("master_clients")
    op.drop_index(op.f("ix_invitations_token"), table_name="invitations")
    op.drop_index(op.f("ix_invitations_target_client_id"), table_name="invitations")
    op.drop_table("invitations")
    op.drop_index(op.f("ix_user_notification_preferences_user_id"), table_name="user_notification_preferences")
    op.drop_table("user_notification_preferences")
    op.drop_table("notification_channels")
    op.drop_index(op.f("ix_master_profiles_public_slug"), table_name="master_profiles")
    op.drop_table("master_profiles")
    op.drop_index(op.f("ix_clients_user_id"), table_name="clients")
    op.drop_table("clients")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_table("retention_policies")
