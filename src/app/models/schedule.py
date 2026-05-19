from __future__ import annotations

import uuid
from datetime import date, time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, Integer, String, Time, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimeStampedModel

if TYPE_CHECKING:
    from app.models.master import MasterProfile


class WeeklyScheduleDay(TimeStampedModel):
    """Recurring weekly template day. Monday=0 … Sunday=6 (ISO weekday style)."""

    __tablename__ = "weekly_schedule_days"
    __table_args__ = (
        UniqueConstraint("master_id", "weekday", name="uq_weekly_schedule_day"),
        CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_weekly_schedule_day_weekday_range"),
        Index("ix_weekly_schedule_days_master_weekday", "master_id", "weekday"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    master_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("master_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    weekday: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    is_closed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    master: Mapped[MasterProfile] = relationship(
        "MasterProfile",
        back_populates="weekly_schedule_days",
    )
    intervals: Mapped[list[WeeklyScheduleInterval]] = relationship(
        "WeeklyScheduleInterval",
        back_populates="day",
        cascade="all, delete-orphan",
        order_by="WeeklyScheduleInterval.sort_order",
    )


class WeeklyScheduleInterval(TimeStampedModel):
    __tablename__ = "weekly_schedule_intervals"
    __table_args__ = (
        UniqueConstraint("day_id", "start_time", name="uq_weekly_schedule_interval_start"),
        CheckConstraint("start_time < end_time", name="ck_weekly_schedule_interval_time_order"),
        Index("ix_weekly_schedule_interval_day_order", "day_id", "sort_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    day_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("weekly_schedule_days.id", ondelete="CASCADE"),
        nullable=False,
    )
    start_time: Mapped[time] = mapped_column(
        Time(timezone=False),
        nullable=False,
    )
    end_time: Mapped[time] = mapped_column(
        Time(timezone=False),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    day: Mapped[WeeklyScheduleDay] = relationship(
        "WeeklyScheduleDay",
        back_populates="intervals",
    )


class ScheduleDateOverride(TimeStampedModel):
    """One-off schedule replacement for a concrete calendar date."""

    __tablename__ = "schedule_date_overrides"
    __table_args__ = (
        UniqueConstraint("master_id", "schedule_date", name="uq_schedule_date_override"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    master_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("master_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    schedule_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    is_closed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    master: Mapped[MasterProfile] = relationship(
        "MasterProfile",
        back_populates="schedule_date_overrides",
    )
    intervals: Mapped[list[ScheduleDateOverrideInterval]] = relationship(
        "ScheduleDateOverrideInterval",
        back_populates="override",
        cascade="all, delete-orphan",
        order_by="ScheduleDateOverrideInterval.sort_order",
    )


class ScheduleDateOverrideInterval(TimeStampedModel):
    __tablename__ = "schedule_date_override_intervals"
    __table_args__ = (
        UniqueConstraint("override_id", "start_time", name="uq_schedule_date_override_interval_start"),
        CheckConstraint("start_time < end_time", name="ck_schedule_date_override_interval_time_order"),
        Index("ix_schedule_date_override_intervals_order", "override_id", "sort_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    override_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("schedule_date_overrides.id", ondelete="CASCADE"),
        nullable=False,
    )
    start_time: Mapped[time] = mapped_column(
        Time(timezone=False),
        nullable=False,
    )
    end_time: Mapped[time] = mapped_column(
        Time(timezone=False),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    override: Mapped[ScheduleDateOverride] = relationship(
        "ScheduleDateOverride",
        back_populates="intervals",
    )
