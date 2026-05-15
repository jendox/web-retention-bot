from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.models.master import MasterProfile
from app.repositories.services import ServiceRepository, get_service_repo

from .exceptions import ServiceHasBookingsError, ServiceNotFoundError


class DeleteServiceUseCase:
    def __init__(self, service_repo: ServiceRepository) -> None:
        self._service_repo = service_repo

    async def execute(self, master: MasterProfile, service_id: UUID) -> None:
        service = await self._service_repo.get_for_master(service_id, master.id)
        if not service:
            raise ServiceNotFoundError from None
        if await self._service_repo.count_bookings_for_service(service_id):
            raise ServiceHasBookingsError from None
        await self._service_repo.delete_entity(service)


def get_delete_service_use_case(
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
) -> DeleteServiceUseCase:
    return DeleteServiceUseCase(service_repo)
