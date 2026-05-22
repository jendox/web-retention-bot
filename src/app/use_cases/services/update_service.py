from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models.master import MasterProfile
from app.models.service import Service
from app.repositories.services import ServiceRepository, get_service_repo
from app.schemas.service import ServiceSchema, ServiceUpdate
from app.use_cases.services.exceptions import (
    ServiceEmptyPatchError,
    ServiceNoFieldsToUpdateError,
    ServiceNotFoundError,
)

__all__ = ["UpdateServiceUseCase", "get_update_service_use_case"]

logger = get_logger("app.service")


class UpdateServiceUseCase:
    def __init__(self, service_repo: ServiceRepository) -> None:
        self._service_repo = service_repo

    async def _get_service(self, service_id: UUID, master_id: UUID) -> Service:
        service = await self._service_repo.get_for_master(service_id, master_id)
        if not service:
            logger.warning("failed", reason="service_not_found")
            raise ServiceNotFoundError()
        return service

    async def __call__(
        self,
        master: MasterProfile,
        service_id: UUID,
        payload: ServiceUpdate,
    ) -> ServiceSchema:
        with log_context(use_case="update_service", master_id=str(master.id), service_id=str(service_id)):
            patch = payload.model_dump(exclude_unset=True)
            if not patch:
                logger.warning("failed", reason="empty_patch")
                raise ServiceEmptyPatchError()

            service = await self._get_service(service_id, master.id)

            changed = service.apply_patch(patch)
            if not changed:
                logger.warning("failed", reason="no_fields_to_update")
                raise ServiceNoFieldsToUpdateError()

            await self._service_repo.flush()
            await self._service_repo.refresh(service)
            logger.info("updated", fields=sorted(patch.keys()))
            return ServiceSchema.model_validate(service)


def get_update_service_use_case(
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
) -> UpdateServiceUseCase:
    return UpdateServiceUseCase(service_repo)
