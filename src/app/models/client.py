"""Standalone client records linked to masters without requiring app accounts."""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.master import MasterProfile


class InvitationStatus(enum.StrEnum):
    pending = "pending"
    linked = "linked"
    revoked = "revoked"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    master_links: Mapped[list["MasterClient"]] = relationship(
        "MasterClient",
        back_populates="client",
        cascade="all, delete-orphan",
    )
    bookings: Mapped[list["Booking"]] = relationship("Booking", back_populates="client")


class MasterClient(Base):
    __tablename__ = "master_clients"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    master_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("master_profiles.id"))
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("clients.id"))
    alias: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    invitation_status: Mapped[InvitationStatus] = mapped_column(
        SAEnum(
            InvitationStatus,
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
            length=32,
        ),
        default=InvitationStatus.linked,
    )

    master: Mapped["MasterProfile"] = relationship("MasterProfile", back_populates="master_clients")
    client: Mapped["Client"] = relationship("Client", back_populates="master_links")
