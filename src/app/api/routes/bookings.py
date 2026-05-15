from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import optional_master_profile, require_master_profile, require_user
from app.core.database import get_db_session
from app.models.master import MasterProfile
from app.models.user import User
from app.repositories.bookings import BookingRepository
from app.schemas.booking import BookingClientListItem, BookingCreate, BookingOut, BookingReschedule
from app.use_cases.booking_updates import cancel_booking, reschedule_booking
from app.use_cases.create_booking import create_booking

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("/me", response_model=list[BookingClientListItem])
async def list_my_bookings_as_client(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(require_user)],
) -> list[BookingClientListItem]:
    repo = BookingRepository(session)
    rows = await repo.list_with_details_for_linked_user(user.id)
    return [
        BookingClientListItem(
            **BookingOut.model_validate(b).model_dump(),
            master_display_name=mname,
            service_name=sname,
        )
        for b, mname, sname in rows
    ]


@router.get("", response_model=list[BookingOut])
async def list_bookings(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> list[BookingOut]:
    repo = BookingRepository(session)
    bookings = await repo.list_for_master(master.id)
    return [BookingOut.model_validate(b) for b in bookings]


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
async def post_booking(
    request: Request,
    payload: BookingCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    master: Annotated[MasterProfile | None, Depends(optional_master_profile)],
) -> BookingOut:
    settings = request.app.state.settings
    actor_id = master.id if master else None
    booking = await create_booking(
        session,
        payload,
        actor_master_id=actor_id,
        slot_step_minutes=settings.AVAILABILITY_SLOT_STEP_MINUTES,
    )
    return BookingOut.model_validate(booking)


@router.post("/{booking_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def post_cancel(
    booking_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> Response:
    await cancel_booking(session, master.id, booking_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{booking_id}/reschedule", response_model=BookingOut)
async def post_reschedule(
    request: Request,
    booking_id: UUID,
    payload: BookingReschedule,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> BookingOut:
    settings = request.app.state.settings
    await reschedule_booking(
        session,
        master.id,
        booking_id,
        payload.start_at,
        slot_step_minutes=settings.AVAILABILITY_SLOT_STEP_MINUTES,
    )
    bookings = BookingRepository(session)
    refreshed = await bookings.get_for_master(booking_id, master.id)
    if not refreshed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Booking disappeared")
    return BookingOut.model_validate(refreshed)
