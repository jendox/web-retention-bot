from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Response, status

from app.api.deps import require_user
from app.core.pagination import Pagination, get_pagination
from app.models.user import User
from app.schemas.booking import (
    BookingCancel,
    BookingClientListItem,
    BookingListScope,
    BookingReschedule,
    ClientBookingCreate,
)
from app.schemas.errors import ErrorDetail
from app.schemas.pagination import PaginatedResponse
from app.use_cases.booking import (
    CancelClientBookingUseCase,
    CreateClientBookingUseCase,
    ListClientBookingsUseCase,
    RescheduleClientBookingUseCase,
    get_cancel_client_booking_use_case,
    get_create_client_booking_use_case,
    get_list_client_bookings_use_case,
    get_reschedule_client_booking_use_case,
)

router = APIRouter(prefix="/bookings", tags=["client-bookings"])


@router.get(
    path="",
    summary="Current user's bookings as client (paginated)",
    description=(
        "Returns a paginated slice of the client's bookings. "
        "`scope=upcoming` — active scheduled visits. "
        "`scope=history` — completed, cancelled, no-show, and past visits."
    ),
    response_model=PaginatedResponse[BookingClientListItem],
    status_code=status.HTTP_200_OK,
    response_description="Bookings visible to the current client user.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorDetail,
            "description": "Missing or invalid session cookie.",
        },
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail},
    },
)
async def list_my_bookings_as_client(
    user: Annotated[User, Depends(require_user)],
    pagination: Annotated[Pagination, Depends(get_pagination)],
    scope: Annotated[
        BookingListScope,
        Query(description="`upcoming` for active visits; `history` for archive."),
    ],
    use_case: Annotated[ListClientBookingsUseCase, Depends(get_list_client_bookings_use_case)],
) -> PaginatedResponse[BookingClientListItem]:
    return await use_case(user.id, pagination, scope=scope)


@router.post(
    path="",
    summary="Create a booking as the current client",
    description=(
        "Books a slot with a master the user is linked to. "
        "The client card is resolved from the master–client link for the authenticated user."
    ),
    response_model=BookingClientListItem,
    status_code=status.HTTP_201_CREATED,
    response_description="Booking created and formatted for the client booking list.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorDetail,
            "description": "Not linked to master or slot unavailable.",
        },
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail},
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail},
        status.HTTP_409_CONFLICT: {"model": ErrorDetail},
    },
)
async def create_booking_as_client(
    payload: ClientBookingCreate,
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[CreateClientBookingUseCase, Depends(get_create_client_booking_use_case)],
) -> BookingClientListItem:
    return await use_case(user=user, payload=payload)


@router.post(
    path="/{booking_id}/cancel",
    summary="Cancel own booking as client",
    description="Cancels an upcoming booking that belongs to the authenticated client user.",
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Booking cancelled; no response body.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail, "description": "Missing or invalid session cookie."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail, "description": "Email not verified."},
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "Booking was not found for this client."},
    },
)
async def post_cancel_my_booking(
    booking_id: UUID,
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[CancelClientBookingUseCase, Depends(get_cancel_client_booking_use_case)],
    payload: Annotated[BookingCancel | None, Body()] = None,
) -> Response:
    await use_case(
        user=user,
        booking_id=booking_id,
        comment=payload.comment if payload else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    path="/{booking_id}/reschedule",
    summary="Reschedule own booking as client",
    description="Moves an upcoming booking owned by the authenticated client user to another available slot.",
    response_model=BookingClientListItem,
    status_code=status.HTTP_200_OK,
    response_description="Rescheduled booking formatted for the client booking list.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorDetail, "description": "Requested slot is unavailable."},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail, "description": "Missing or invalid session cookie."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail, "description": "Email not verified."},
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "Booking was not found for this client."},
        status.HTTP_409_CONFLICT: {
            "model": ErrorDetail,
            "description": "Another scheduled booking overlaps the requested time.",
        },
    },
)
async def post_reschedule_my_booking(
    booking_id: UUID,
    payload: BookingReschedule,
    user: Annotated[User, Depends(require_user)],
    use_case: Annotated[RescheduleClientBookingUseCase, Depends(get_reschedule_client_booking_use_case)],
) -> BookingClientListItem:
    return await use_case(
        user=user,
        booking_id=booking_id,
        start_at=payload.start_at,
        comment=payload.comment,
    )
