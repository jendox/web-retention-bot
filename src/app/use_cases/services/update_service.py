from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models.master import MasterProfile
from app.models.service import Service
from app.repositories.services import ServiceRepository, get_service_repo
from app.schemas.service import ServiceSchema, ServiceUpdate

from .exceptions import ServiceNotFoundError

logger = get_logger("app.service")

_NOT_NULLABLE_FIELDS = frozenset({
    "name",
    "duration_min",
    "price",
    "currency",
    "is_active",
    "sort_order",
})


class UpdateServiceUseCase:
    def __init__(self, service_repo: ServiceRepository) -> None:
        self._service_repo = service_repo

    async def _get_service(self, service_id: UUID, master_id: UUID) -> Service:
        service = await self._service_repo.get_for_master(service_id, master_id)
        if not service:
            logger.warning("failed", reason="service_not_found")
            raise ServiceNotFoundError from None
        return service

    @staticmethod
    def _apply_patch_updates(patch: dict[str, Any], service: Service) -> None:
        for key, value in patch.items():
            if key in _NOT_NULLABLE_FIELDS and value is None:
                continue
            setattr(service, key, value)

    async def execute(
        self,
        master: MasterProfile,
        service_id: UUID,
        payload: ServiceUpdate,
    ) -> ServiceSchema:
        with log_context(use_case="update_service", master_id=str(master.id), service_id=str(service_id)):
            patch = payload.model_dump(exclude_unset=True)
            service = await self._get_service(service_id, master.id)

            self._apply_patch_updates(patch, service)

            await self._service_repo.flush()
            await self._service_repo.refresh(service)
            logger.info("updated", fields=sorted(patch.keys()))
            return ServiceSchema.model_validate(service)


def get_update_service_use_case(
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
) -> UpdateServiceUseCase:
    return UpdateServiceUseCase(service_repo)
