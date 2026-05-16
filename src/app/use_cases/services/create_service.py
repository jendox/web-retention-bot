from typing import Annotated

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models.master import MasterProfile
from app.models.service import Service
from app.repositories.services import ServiceRepository, get_service_repo
from app.schemas.service import ServiceCreate, ServiceOut

logger = get_logger("app.service")


class CreateServiceUseCase:
    def __init__(self, service_repo: ServiceRepository) -> None:
        self._service_repo = service_repo

    async def execute(self, master: MasterProfile, payload: ServiceCreate) -> ServiceOut:
        with log_context(use_case="create_service", master_id=str(master.id)):
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
            logger.info("created", service_id=str(created.id), duration_min=created.duration_min)
            return ServiceOut.model_validate(created)


def get_create_service_use_case(
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
) -> CreateServiceUseCase:
    return CreateServiceUseCase(service_repo)
