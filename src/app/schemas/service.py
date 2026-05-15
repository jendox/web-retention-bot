"""Service CRUD shapes."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.currency import Currency


class ServiceCreate(BaseModel):
    name: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    duration_min: int = Field(gt=0)
    price: Decimal = Field(ge=Decimal("0"))
    currency: Currency | None = None
    is_active: bool = True
    sort_order: int = 0


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    duration_min: int | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, ge=Decimal("0"))
    currency: Currency | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    master_id: UUID
    name: str
    description: str | None
    duration_min: int
    price: Decimal
    currency: Currency
    is_active: bool
    sort_order: int
