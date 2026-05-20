from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.currency import DEFAULT_MASTER_CURRENCY, Currency
from app.models.base import TimeStampedModel

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.client import MasterClient
    from app.models.invitation import Invitation
    from app.models.schedule import ScheduleDateOverride, WeeklyScheduleDay
    from app.models.service import Service
    from app.models.user import User


class MasterProfile(TimeStampedModel):
    __tablename__ = "master_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    public_slug: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    default_currency: Mapped[Currency] = mapped_column(
        SAEnum(
            Currency,
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
            length=3,
        ),
        default=DEFAULT_MASTER_CURRENCY,
    )
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    telegram: Mapped[str | None] = mapped_column(String(100), nullable=True)
    viber: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="master_profile")

    weekly_schedule_days: Mapped[list[WeeklyScheduleDay]] = relationship(
        "WeeklyScheduleDay",
        back_populates="master",
        cascade="all, delete-orphan",
    )
    schedule_date_overrides: Mapped[list[ScheduleDateOverride]] = relationship(
        "ScheduleDateOverride",
        back_populates="master",
        cascade="all, delete-orphan",
    )
    services: Mapped[list[Service]] = relationship("Service", back_populates="master")
    master_clients: Mapped[list[MasterClient]] = relationship(
        "MasterClient",
        back_populates="master",
        cascade="all, delete-orphan",
    )
    invitations: Mapped[list[Invitation]] = relationship(
        "Invitation",
        back_populates="master",
        cascade="all, delete-orphan",
    )
    bookings: Mapped[list[Booking]] = relationship(
        "Booking",
        back_populates="master",
        cascade="all, delete-orphan",
    )
