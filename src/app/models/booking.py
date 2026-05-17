"""Bookings anchor service snapshots for historical accuracy."""

import enum
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.master import MasterProfile
    from app.models.service import Service


class BookingStatus(enum.StrEnum):
    scheduled = "scheduled"
    cancelled = "cancelled"


class Booking(Base):
    __tablename__ = "bookings"

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
        default=BookingStatus.scheduled,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    master: Mapped["MasterProfile"] = relationship("MasterProfile", back_populates="bookings")
    client: Mapped["Client"] = relationship("Client", back_populates="bookings")
    service: Mapped["Service"] = relationship("Service", back_populates="bookings")
