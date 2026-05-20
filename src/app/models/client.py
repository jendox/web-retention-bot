from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimeStampedModel

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.master import MasterProfile
    from app.models.user import User


class InvitationStatus(enum.StrEnum):
    PENDING = "PENDING"
    LINKED = "LINKED"
    REVOKED = "REVOKED"


class Client(TimeStampedModel):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    display_name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    user: Mapped[User | None] = relationship("User", back_populates="client_profiles")

    master_links: Mapped[list[MasterClient]] = relationship(
        "MasterClient",
        back_populates="client",
        cascade="all, delete-orphan",
    )
    bookings: Mapped[list[Booking]] = relationship("Booking", back_populates="client")


class MasterClient(Base):
    __tablename__ = "master_clients"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    master_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("master_profiles.id"))
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("clients.id"))
    alias: Mapped[str | None] = mapped_column(String(200), nullable=True)
    client_alias: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    linked_account_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    invite_email_mismatch: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    invitation_status: Mapped[InvitationStatus] = mapped_column(
        SAEnum(
            InvitationStatus,
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
            length=32,
        ),
        default=InvitationStatus.LINKED,
    )

    master: Mapped[MasterProfile] = relationship("MasterProfile", back_populates="master_clients")
    client: Mapped[Client] = relationship("Client", back_populates="master_links")
