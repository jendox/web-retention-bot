from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Uuid, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimeStampedModel

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.master import MasterProfile
    from app.models.service import Service


class BookingStatus(enum.StrEnum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"
    CANCELLED = "CANCELLED"

    @property
    def blocks_calendar(self) -> bool:
        return self is BookingStatus.SCHEDULED

    @property
    def is_terminal(self) -> bool:
        return self in {BookingStatus.COMPLETED, BookingStatus.NO_SHOW, BookingStatus.CANCELLED}


class Booking(TimeStampedModel):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ch_start_end_at"),
        Index("ix_master_status_start_at", "master_id", "status", "start_at"),
        Index("ix_master_start_at", "master_id", "start_at"),
        Index("ix_client_start_at", "client_id", "start_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    master_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("master_profiles.id"))
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("clients.id"))
    service_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("services.id"))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_min: Mapped[int] = mapped_column(Integer)
    price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency_snapshot: Mapped[str] = mapped_column(String(3))
    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(
            BookingStatus,
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
            length=32,
        ),
        default=BookingStatus.SCHEDULED,
    )

    master: Mapped["MasterProfile"] = relationship("MasterProfile", back_populates="bookings")
    client: Mapped["Client"] = relationship("Client", back_populates="bookings")
    service: Mapped["Service"] = relationship("Service", back_populates="bookings")

    def is_upcoming(self, now: datetime | None = None) -> bool:
        if now is None:
            now = datetime.now(UTC)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        return self.status.blocks_calendar and self.end_at >= now

    def is_history(self, now: datetime | None = None) -> bool:
        return not self.is_upcoming(now)
