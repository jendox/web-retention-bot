from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models.master import MasterProfile
from app.repositories.services import ServiceRepository, get_service_repo
from app.schemas.service import ServiceSchema
from app.use_cases.services.exceptions import ServiceNotFoundError

__all__ = ["GetServiceUseCase", "get_get_service_use_case"]

logger = get_logger("app.service")


class GetServiceUseCase:
    def __init__(self, service_repo: ServiceRepository) -> None:
        self._service_repo = service_repo

    async def __call__(self, master: MasterProfile, service_id: UUID) -> ServiceSchema:
        with log_context(use_case="get_service", service_id=str(service_id)):
            service = await self._service_repo.get_for_master(service_id, master.id)
            if not service:
                logger.warning("failed", reason="service_not_found")
                raise ServiceNotFoundError()
            return ServiceSchema.model_validate(service)


def get_get_service_use_case(
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
) -> GetServiceUseCase:
    return GetServiceUseCase(service_repo)
