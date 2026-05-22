from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models import Service
from app.models.master import MasterProfile
from app.repositories.services import ServiceRepository, get_service_repo
from app.use_cases.services.exceptions import ServiceHasBookingsError, ServiceNotFoundError

__all__ = ["DeleteServiceUseCase", "get_delete_service_use_case"]

logger = get_logger("app.service")


class DeleteServiceUseCase:
    def __init__(self, service_repo: ServiceRepository) -> None:
        self._service_repo = service_repo

    async def _get_service(self, service_id: UUID, master_id: UUID) -> Service:
        service = await self._service_repo.get_for_master(service_id, master_id)
        if not service:
            logger.warning("failed", reason="service_not_found")
            raise ServiceNotFoundError()
        return service

    async def execute(self, master: MasterProfile, service_id: UUID) -> None:
        with log_context(use_case="delete_service", master_id=str(master.id), service_id=str(service_id)):
            service = await self._get_service(service_id, master.id)

            if await self._service_repo.count_bookings_for_service(service_id):
                logger.warning("failed", reason="has_bookings")
                raise ServiceHasBookingsError()

            await self._service_repo.delete_entity(service)
            logger.info("deleted")


def get_delete_service_use_case(
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
) -> DeleteServiceUseCase:
    return DeleteServiceUseCase(service_repo)
