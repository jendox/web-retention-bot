from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.models.master import MasterProfile
from app.repositories.services import ServiceRepository, get_service_repo
from app.schemas.service import ServiceOut, ServiceUpdate

from .exceptions import ServiceNotFoundError


class UpdateServiceUseCase:
    def __init__(self, service_repo: ServiceRepository) -> None:
        self._service_repo = service_repo

    async def execute(
        self,
        master: MasterProfile,
        service_id: UUID,
        payload: ServiceUpdate,
    ) -> ServiceOut:
        service = await self._service_repo.get_for_master(service_id, master.id)
        if not service:
            raise ServiceNotFoundError from None
        if payload.name is not None:
            service.name = payload.name
        if payload.description is not None:
            service.description = payload.description
        if payload.duration_min is not None:
            service.duration_min = payload.duration_min
        if payload.price is not None:
            service.price = payload.price
        if payload.currency is not None:
            service.currency = payload.currency
        if payload.is_active is not None:
            service.is_active = payload.is_active
        if payload.sort_order is not None:
            service.sort_order = payload.sort_order
        await self._service_repo.session.flush()
        await self._service_repo.session.refresh(service)
        return ServiceOut.model_validate(service)


def get_update_service_use_case(
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
) -> UpdateServiceUseCase:
    return UpdateServiceUseCase(service_repo)
