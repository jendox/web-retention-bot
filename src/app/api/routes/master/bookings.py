from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Response, status

from app.api.deps import require_master_profile
from app.core.pagination import Pagination, get_pagination
from app.models.master import MasterProfile
from app.schemas.booking import (
    BookingAttendanceMark,
    BookingCancel,
    BookingCreate,
    BookingListScope,
    BookingMonthlyRevenueOut,
    BookingOut,
    BookingReschedule,
)
from app.schemas.errors import ErrorDetail
from app.schemas.pagination import PaginatedResponse
from app.use_cases.booking import (
    CancelMasterBookingUseCase,
    CreateMasterBookingUseCase,
    GetMasterMonthlyRevenueUseCase,
    ListMasterBookingsUseCase,
    MarkMasterBookingAttendanceUseCase,
    RescheduleMasterBookingUseCase,
    get_cancel_master_booking_use_case,
    get_create_master_booking_use_case,
    get_list_master_bookings_use_case,
    get_mark_master_booking_attendance_use_case,
    get_master_monthly_revenue_use_case,
    get_reschedule_master_booking_use_case,
)

router = APIRouter(prefix="/bookings", tags=["master-bookings"])


@router.get(
    path="/stats/monthly-revenue",
    summary="Completed visit revenue for the current calendar month",
    description=(
        "Aggregates `price_snapshot` for bookings with status COMPLETED whose `start_at` "
        "falls in the current calendar month in the master's timezone. NO_SHOW and CANCELLED are excluded."
    ),
    response_model=BookingMonthlyRevenueOut,
    status_code=status.HTTP_200_OK,
    response_description="Current-month completed revenue summary.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail, "description": "Missing or invalid session cookie."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail, "description": "Email not verified."},
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "Current user has no master profile."},
    },
)
async def get_monthly_revenue(
    master: Annotated[MasterProfile, Depends(require_master_profile)],
    use_case: Annotated[GetMasterMonthlyRevenueUseCase, Depends(get_master_monthly_revenue_use_case)],
) -> BookingMonthlyRevenueOut:
    return await use_case(master)


@router.get(
    path="",
    summary="Current master's bookings (paginated)",
    description=(
        "Returns a paginated slice of the master's bookings. "
        "`scope=upcoming` — active scheduled visits (`SCHEDULED`, not ended yet). "
        "`scope=history` — completed, cancelled, no-show, and past visits still awaiting auto-complete."
    ),
    response_model=PaginatedResponse[BookingOut],
    status_code=status.HTTP_200_OK,
    response_description="Bookings owned by the current master.",
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
async def list_bookings(
    master: Annotated[MasterProfile, Depends(require_master_profile)],
    pagination: Annotated[Pagination, Depends(get_pagination)],
    scope: Annotated[
        BookingListScope,
        Query(description="`upcoming` for active visits; `history` for archive."),
    ],
    use_case: Annotated[ListMasterBookingsUseCase, Depends(get_list_master_bookings_use_case)],
    client_id: Annotated[UUID | None, Query(description="Optional filter by client.")] = None,
    service_id: Annotated[UUID | None, Query(description="Optional filter by service.")] = None,
) -> PaginatedResponse[BookingOut]:
    return await use_case(
        master.id,
        pagination,
        scope=scope,
        client_id=client_id,
        service_id=service_id,
    )


@router.post(
    path="",
    summary="Create a booking",
    description=(
        "Creates a booking for an available service slot. The current authenticated master can create bookings "
        "only for clients linked to their profile."
    ),
    response_model=BookingOut,
    status_code=status.HTTP_201_CREATED,
    response_description="Booking created.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorDetail,
            "description": "Unknown client linkage or requested slot is unavailable.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorDetail,
            "description": "Missing or invalid master session.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "Master profile or service was not found.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorDetail,
            "description": "Another scheduled booking overlaps the requested time.",
        },
    },
)
async def create_booking(
    payload: BookingCreate,
    master: Annotated[MasterProfile, Depends(require_master_profile)],
    use_case: Annotated[CreateMasterBookingUseCase, Depends(get_create_master_booking_use_case)],
) -> BookingOut:
    return await use_case(payload, master=master)


@router.post(
    path="/{booking_id}/cancel",
    summary="Cancel a booking",
    description="Cancels a booking owned by the current master.",
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Booking cancelled.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorDetail,
            "description": "Missing or invalid session cookie.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "The current user has no master profile, or booking was not found.",
        },
    },
)
async def cancel_booking(
    booking_id: UUID,
    master: Annotated[MasterProfile, Depends(require_master_profile)],
    use_case: Annotated[CancelMasterBookingUseCase, Depends(get_cancel_master_booking_use_case)],
    payload: Annotated[BookingCancel | None, Body()] = None,
) -> Response:
    await use_case(
        master=master,
        booking_id=booking_id,
        comment=payload.comment if payload else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    path="/{booking_id}/reschedule",
    summary="Reschedule a booking",
    description="Moves an active booking owned by the current master to another available slot.",
    response_model=BookingOut,
    status_code=status.HTTP_200_OK,
    response_description="Booking rescheduled.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorDetail,
            "description": "Requested slot is unavailable.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorDetail,
            "description": "Missing or invalid session cookie.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": (
                "The current user has no master profile, active booking was not found, or service is missing."
            ),
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorDetail,
            "description": "Another scheduled booking overlaps the requested time.",
        },
    },
)
async def reschedule_booking(
    booking_id: UUID,
    payload: BookingReschedule,
    master: Annotated[MasterProfile, Depends(require_master_profile)],
    use_case: Annotated[RescheduleMasterBookingUseCase, Depends(get_reschedule_master_booking_use_case)],
) -> BookingOut:
    return await use_case(
        master=master,
        booking_id=booking_id,
        start_at=payload.start_at,
        comment=payload.comment,
    )


@router.post(
    path="/{booking_id}/attendance",
    summary="Mark visit attendance",
    description=(
        "For completed visits awaiting confirmation: mark the client as attended "
        "(keeps `COMPLETED`) or as no-show (`NO_SHOW`)."
    ),
    response_model=BookingOut,
    status_code=status.HTTP_200_OK,
    response_description="Booking updated with attendance outcome.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorDetail,
            "description": "Booking is not awaiting attendance confirmation.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorDetail,
            "description": "Missing or invalid session cookie.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "Booking not found.",
        },
    },
)
async def mark_attendance(
    booking_id: UUID,
    payload: BookingAttendanceMark,
    master: Annotated[MasterProfile, Depends(require_master_profile)],
    use_case: Annotated[
        MarkMasterBookingAttendanceUseCase,
        Depends(get_mark_master_booking_attendance_use_case),
    ],
) -> BookingOut:
    return await use_case(master_id=master.id, booking_id=booking_id, attended=payload.attended)
