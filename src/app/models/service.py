from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.currency import DEFAULT_MASTER_CURRENCY, Currency
from app.models.base import PatchableMixin, TimeStampedModel

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.master import MasterProfile


class Service(TimeStampedModel, PatchableMixin):
    __tablename__ = "services"
    __patchable_fields__ = frozenset({
        "name",
        "description",
        "duration_min",
        "price",
        "currency",
        "is_active",
        "sort_order",
    })
    __patch_ignore_none_fields__ = frozenset({
        "name",
        "duration_min",
        "price",
        "currency",
        "is_active",
        "sort_order",
    })

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    master_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("master_profiles.id"))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    duration_min: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[Currency] = mapped_column(
        SAEnum(
            Currency,
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
            length=3,
        ),
        default=DEFAULT_MASTER_CURRENCY,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    master: Mapped[MasterProfile] = relationship("MasterProfile", back_populates="services")
    bookings: Mapped[list[Booking]] = relationship(
        "Booking",
        back_populates="service",
    )
