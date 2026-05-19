from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.models.master import MasterProfile
from app.repositories.services import ServiceRepository, get_service_repo
from app.schemas.service import ServiceSchema

from .exceptions import ServiceNotFoundError


class GetServiceUseCase:
    def __init__(self, service_repo: ServiceRepository) -> None:
        self._service_repo = service_repo

    async def execute(self, master: MasterProfile, service_id: UUID) -> ServiceSchema:
        service = await self._service_repo.get_for_master(service_id, master.id)
        if not service:
            raise ServiceNotFoundError from None
        return ServiceSchema.model_validate(service)


def get_get_service_use_case(
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
) -> GetServiceUseCase:
    return GetServiceUseCase(service_repo)
