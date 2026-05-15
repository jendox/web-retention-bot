from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_master_profile, require_user
from app.core.database import get_db_session
from app.models.master import MasterProfile
from app.models.user import User
from app.repositories.invitations import InvitationRepository
from app.repositories.services import ServiceRepository
from app.schemas.invitation import (
    InvitationAccept,
    InvitationAcceptOut,
    InvitationCreate,
    InvitationLandingResponse,
    InvitationOut,
)
from app.schemas.service import ServiceOut
from app.services.notifications.dispatcher import NotificationDispatcher, get_notification_dispatcher
from app.use_cases.accept_invitation import accept_invitation_use_case
from app.use_cases.create_invitation import create_invitation_use_case

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.post("", response_model=InvitationOut, status_code=status.HTTP_201_CREATED)
async def post_invitation(
    payload: InvitationCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> InvitationOut:
    invitation = await create_invitation_use_case(
        session,
        master_id=master.id,
        expires_hours=payload.expires_hours,
        target_email=str(payload.target_email).lower() if payload.target_email else None,
        target_client_id=payload.target_client_id,
        replace=payload.replace,
    )
    return InvitationOut.model_validate(invitation)


@router.get("/{token}", response_model=InvitationLandingResponse)
async def get_invitation_landing(token: str, session: Annotated[AsyncSession, Depends(get_db_session)]):
    repo = InvitationRepository(session)
    services_repo = ServiceRepository(session)
    invite = await repo.get_by_token(token)
    if not invite:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    if invite.revoked_at is not None:
        raise HTTPException(status.HTTP_410_GONE, detail="Invitation revoked")
    if invite.expires_at < datetime.now(UTC):
        raise HTTPException(status.HTTP_410_GONE, detail="Invitation expired")
    master_profile = invite.master
    target = invite.target_client
    invite_kind: Literal["open", "client"] = "client" if invite.target_client_id else "open"
    master_record_has_email = bool(target and target.email and target.email.strip())

    svc_list_raw = await services_repo.list_for_master(master_profile.id)
    services_public = [
        ServiceOut.model_validate(service)
        for service in svc_list_raw
        if service.is_active
    ]
    landing = InvitationLandingResponse(
        master_display_name=master_profile.display_name,
        timezone=master_profile.timezone,
        token=invite.token,
        expires_at=invite.expires_at,
        accepted_at=invite.accepted_at,
        linked_client_id=invite.linked_client_id,
        services=services_public,
        invite_kind=invite_kind,
        master_record_has_email=master_record_has_email,
    )
    return landing


@router.post("/{token}/accept", response_model=InvitationAcceptOut)
async def post_accept_invitation(
    token: str,
    payload: InvitationAccept,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(require_user)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> InvitationAcceptOut:
    client_id, mismatch = await accept_invitation_use_case(session, dispatcher, token, payload, user)
    return InvitationAcceptOut(client_id=client_id, email_mismatch_with_master_record=mismatch)
