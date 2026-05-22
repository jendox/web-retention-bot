from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.schemas.availability import SlotOut
from app.schemas.errors import ErrorDetail
from app.use_cases.booking.available_slots import AvailableSlotsUseCase, get_available_slots_use_case

router = APIRouter(prefix="/availability", tags=["client-availability"])


@router.get(
    path="",
    summary="Available booking slots",
    description=(
        "Returns bookable start times for a service on a master's calendar date. "
        "The date is interpreted in the master's timezone."
    ),
    response_model=list[SlotOut],
    status_code=status.HTTP_200_OK,
    response_description="Available start times for the requested service and date.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorDetail,
            "description": "The requested date is in the past or outside the booking horizon.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "Master or active service was not found.",
        },
    },
)
async def availability_slots(
    master_id: Annotated[UUID, Query(description="Master profile identifier.")],
    service_id: Annotated[UUID, Query(description="Service identifier owned by the master.")],
    day: Annotated[date, Query(alias="date", description="Master-local calendar date.")],
    use_case: Annotated[AvailableSlotsUseCase, Depends(get_available_slots_use_case)],
) -> list[SlotOut]:
    return await use_case(
        master_id=master_id,
        service_id=service_id,
        calendar_day=day,
    )
