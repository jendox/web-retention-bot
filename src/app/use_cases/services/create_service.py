from typing import Annotated

from fastapi import Depends

from app.models.master import MasterProfile
from app.models.service import Service
from app.repositories.services import ServiceRepository, get_service_repo
from app.schemas.service import ServiceCreate, ServiceOut


class CreateServiceUseCase:
    def __init__(self, service_repo: ServiceRepository) -> None:
        self._service_repo = service_repo

    async def execute(self, master: MasterProfile, payload: ServiceCreate) -> ServiceOut:
        currency = payload.currency if payload.currency is not None else master.default_currency
        service = Service(
            master_id=master.id,
            name=payload.name,
            description=payload.description,
            duration_min=payload.duration_min,
            price=payload.price,
            currency=currency,
            is_active=payload.is_active,
            sort_order=payload.sort_order,
        )
        created = await self._service_repo.create(service)
        return ServiceOut.model_validate(created)


def get_create_service_use_case(
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
) -> CreateServiceUseCase:
    return CreateServiceUseCase(service_repo)
