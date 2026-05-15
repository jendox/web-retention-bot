"""Weekly recurrence and per-day overrides for master availability."""

import uuid
from datetime import date, time
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, String, Time, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.master import MasterProfile


class WeeklyScheduleRule(Base):
    """Monday=0 … Sunday=6 (ISO weekday style)."""

    __tablename__ = "weekly_schedule_rules"
    __table_args__ = (UniqueConstraint("master_id", "weekday", "start_time", name="uq_weekly_slot"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    master_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("master_profiles.id"))
    weekday: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time(timezone=False))
    end_time: Mapped[time] = mapped_column(Time(timezone=False))

    master: Mapped["MasterProfile"] = relationship(
        "MasterProfile",
        back_populates="weekly_rules",
    )


class WorkdayOverride(Base):
    __tablename__ = "workday_overrides"
    __table_args__ = (UniqueConstraint("master_id", "override_date", name="uq_override_day"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    master_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("master_profiles.id"))
    override_date: Mapped[date] = mapped_column(Date)
    is_closed: Mapped[bool] = mapped_column(default=False)
    start_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    master: Mapped["MasterProfile"] = relationship(
        "MasterProfile",
        back_populates="workday_overrides",
    )
