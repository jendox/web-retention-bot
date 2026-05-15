from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import HTTPException, Query, status

PAGE_SIZE_DEFAULT = 10
ALLOWED_PAGE_SIZES = (10, 25, 50)
PAGE_SIZE_MIN = min(ALLOWED_PAGE_SIZES)
PAGE_SIZE_MAX = max(ALLOWED_PAGE_SIZES)


@dataclass(frozen=True, slots=True)
class Pagination:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def get_pagination(
    page: Annotated[int, Query(ge=1, description="Номер страницы (с 1).")] = 1,
    page_size: Annotated[
        int,
        Query(
            ge=PAGE_SIZE_MIN,
            le=PAGE_SIZE_MAX,
            description="Число элементов на странице (допустимо: 10, 25 или 50).",
        ),
    ] = PAGE_SIZE_DEFAULT,
) -> Pagination:
    if page_size not in ALLOWED_PAGE_SIZES:
        allowed = ", ".join(str(x) for x in ALLOWED_PAGE_SIZES)
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"page_size must be one of: {allowed}",
        )
    return Pagination(page=page, page_size=page_size)
