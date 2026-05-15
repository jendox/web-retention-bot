from __future__ import annotations

from pydantic import BaseModel


class PaginatedResponse[T](BaseModel):
    """Стандартная обёртка для постраничных списков."""

    items: list[T]
    total: int
    page: int
    page_size: int
