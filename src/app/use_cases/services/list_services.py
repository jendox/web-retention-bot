from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.pagination import Pagination
from app.core.structured_logging import get_logger, log_context
from app.models.master import MasterProfile
from app.repositories.services import ServiceRepository, get_service_repo
from app.schemas.pagination import PaginatedResponse
from app.schemas.service import ServiceSchema

__all__ = ["ListServicesUseCase", "get_list_services_use_case"]

logger = get_logger("app.service")


class ListServicesUseCase:
    def __init__(self, service_repo: ServiceRepository) -> None:
        self._service_repo = service_repo

    async def __call__(
        self,
        master: MasterProfile,
        pagination: Pagination,
        *,
        is_active: bool | None,
        search: str | None = None,
    ) -> PaginatedResponse[ServiceSchema]:
        with log_context(use_case="list_services", master_id=str(master.id)):
            normalized_search = search.strip() if search and search.strip() else None
            total = await self._service_repo.count_for_master(master.id, is_active=is_active, search=normalized_search)
            rows = await self._service_repo.list_page_for_master(
                master.id,
                limit=pagination.page_size,
                offset=pagination.offset,
                is_active=is_active,
                search=normalized_search,
            )
            items = [ServiceSchema.model_validate(svc) for svc in rows]
            return PaginatedResponse(
                items=items,
                total=total,
                page=pagination.page,
                page_size=pagination.page_size,
            )


def get_list_services_use_case(
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
) -> ListServicesUseCase:
    return ListServicesUseCase(service_repo)
