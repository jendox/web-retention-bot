from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_master_profile
from app.models.master import MasterProfile
from app.schemas.errors import ErrorDetail
from app.schemas.master import (
    MasterProfileSchema,
    MasterProfileUpdate,
    MasterScheduleOut,
    MasterScheduleUpsert,
)
from app.use_cases.master import UpdateMasterProfileUseCase, get_update_master_profile_use_case
from app.use_cases.schedule import (
    GetMasterScheduleUseCase,
    ReplaceMasterScheduleUseCase,
    ScheduleBookingConflictError,
    get_get_master_schedule_use_case,
    get_replace_master_schedule_use_case,
)

router = APIRouter(prefix="/masters", tags=["masters"])


@router.get(
    path="/me",
    summary="Current master profile",
    description=(
        "Returns the master profile linked to the current authenticated user. "
        "Responds with 404 when the user does not have a master profile."
    ),
    response_model=MasterProfileSchema,
    status_code=status.HTTP_200_OK,
    response_description="Master profile for the current user.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorDetail,
            "description": "Missing or invalid session cookie.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "The current user does not have a master profile.",
        },
    },
)
async def profile_me(
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> MasterProfileSchema:
    return MasterProfileSchema.model_validate(master)


@router.put(
    path="/me",
    summary="Update current master profile",
    description=(
        "Applies a partial update to the current user's master profile. Nullable fields such as `public_slug` "
        "may be cleared; non-nullable profile fields ignore explicit null values."
    ),
    response_model=MasterProfileSchema,
    status_code=status.HTTP_200_OK,
    response_description="Updated master profile.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorDetail,
            "description": "Missing or invalid session cookie.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "The current user does not have a master profile.",
        },
    },
)
async def profile_update(
    payload: MasterProfileUpdate,
    use_case: Annotated[UpdateMasterProfileUseCase, Depends(get_update_master_profile_use_case)],
) -> MasterProfileSchema:
    return await use_case(payload)


@router.get(
    path="/me/schedule",
    summary="Current master schedule",
    description=(
        "Returns the recurring weekly schedule and date-specific schedule overrides for the current master. "
        "Date overrides replace the weekly template for their calendar date."
    ),
    response_model=MasterScheduleOut,
    status_code=status.HTTP_200_OK,
    response_description="Current weekly schedule and date overrides.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorDetail,
            "description": "Missing or invalid session cookie.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "The current user does not have a master profile.",
        },
    },
)
async def get_schedule_route(
    use_case: Annotated[GetMasterScheduleUseCase, Depends(get_get_master_schedule_use_case)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> MasterScheduleOut:
    return await use_case(master.id)


@router.put(
    path="/me/schedule",
    summary="Replace current master schedule",
    description=(
        "Replaces the full weekly schedule and all date-specific overrides for the current master in one request. "
        "The change is rejected when it would move an existing future booking outside working hours."
    ),
    response_model=MasterScheduleOut,
    status_code=status.HTTP_200_OK,
    response_description="Updated weekly schedule and date overrides.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorDetail,
            "description": "Invalid schedule payload.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorDetail,
            "description": "Missing or invalid session cookie.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "The current user does not have a master profile.",
        },
        status.HTTP_409_CONFLICT: {
            "description": "Schedule changes affect existing future bookings.",
        },
    },
)
async def put_schedule_route(
    payload: MasterScheduleUpsert,
    master: Annotated[MasterProfile, Depends(require_master_profile)],
    use_case: Annotated[ReplaceMasterScheduleUseCase, Depends(get_replace_master_schedule_use_case)],
) -> MasterScheduleOut:
    try:
        return await use_case(master, payload)
    except ScheduleBookingConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Schedule changes affect existing bookings.",
                "bookings": [
                    {
                        "id": str(booking.id),
                        "start_at": booking.start_at.isoformat(),
                        "end_at": booking.end_at.isoformat(),
                    }
                    for booking in exc.conflicts
                ],
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
