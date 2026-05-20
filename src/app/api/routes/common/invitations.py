from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_master_profile, require_user
from app.models.master import MasterProfile
from app.models.user import User
from app.schemas.errors import ErrorDetail
from app.schemas.invitation import (
    InvitationAccept,
    InvitationAcceptOut,
    InvitationCreate,
    InvitationLandingResponse,
    InvitationOut,
)
from app.use_cases.invitations import (
    AcceptInvitationError,
    AcceptInvitationUseCase,
    CreateInvitationError,
    CreateInvitationUseCase,
    InvitationLandingUseCase,
    LandingInvitationError,
    get_accept_invitation_use_case,
    get_create_invitation_use_case,
    get_invitation_landing_use_case,
)

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.post(
    path="",
    summary="Create an invitation link",
    description=(
        "Creates a tokenized invitation for the current master. Without `target_client_id`, the link is a general "
        "open invite: when a verified client accepts it, the system creates a new client card and links it to the "
        "master. With `target_client_id`, the link is bound to an existing manual client card owned by the master; "
        "accepting the link attaches that card to the client's user account. If an active pending invitation already "
        "exists for the same client card, the request returns 409 unless `replace=true`, in which case old pending "
        "links for that card are revoked before the new link is created."
    ),
    response_model=InvitationOut,
    status_code=status.HTTP_201_CREATED,
    response_description="Invitation token and expiration metadata. Build the public URL as `/invite/{token}`.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorDetail,
            "description": "Session missing or invalid (handled by dependency).",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "No master profile for the current user, or `target_client_id` does not belong to it.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorDetail,
            "description": (
                "The target client card is already linked to a user account, or an active pending invitation "
                "already exists and `replace` was not requested."
            ),
        },
    },
)
async def post_invitation(
    payload: InvitationCreate,
    use_case: Annotated[CreateInvitationUseCase, Depends(get_create_invitation_use_case)],
    master: Annotated[MasterProfile, Depends(require_master_profile)],
) -> InvitationOut:
    try:
        return await use_case(
            master_id=master.id,
            expires_hours=payload.expires_hours,
            target_email=str(payload.target_email).lower() if payload.target_email else None,
            target_client_id=payload.target_client_id,
            replace=payload.replace,
        )
    except CreateInvitationError as error:
        status_code = error.status_code if error.status_code else status.HTTP_400_BAD_REQUEST
        error_message = error.error_message if error.error_message else "Create invitation error."
        raise HTTPException(status_code=status_code, detail=error_message) from None


@router.get(
    path="/{token}",
    summary="Read public invitation landing data",
    description=(
        "Returns the public data needed to render an invitation page: master display name, timezone, expiration, "
        "acceptance state, linked client id when already accepted, active services, and whether the invite is a "
        "general open link or a link bound to a specific client card. This endpoint is intentionally public so a "
        "client can inspect the invitation before signing in or registering. Revoked or expired links return 410."
    ),
    response_model=InvitationLandingResponse,
    response_description="Public invitation snapshot plus active services available for booking after acceptance.",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": "No invitation exists for the supplied token.",
        },
        status.HTTP_410_GONE: {
            "model": ErrorDetail,
            "description": "The invitation was revoked or its expiration time has passed.",
        },
    },
)
async def get_invitation_landing(
    token: str,
    use_case: Annotated[InvitationLandingUseCase, Depends(get_invitation_landing_use_case)],
) -> InvitationLandingResponse:
    try:
        return await use_case(token)
    except LandingInvitationError as error:
        status_code = error.status_code if error.status_code else status.HTTP_400_BAD_REQUEST
        error_message = error.error_message if error.error_message else "Invitation error."
        raise HTTPException(status_code=status_code, detail=error_message) from None


@router.post(
    path="/{token}/accept",
    summary="Accept an invitation as the current client user",
    description=(
        "Accepts an invitation for the authenticated, email-verified user. For a general open invite, this creates "
        "a new client card, links it to the master, and attaches it to the user account. For a client-bound invite, "
        "this attaches the existing client card to the user account and updates the display name and phone from the "
        "request body. The master cannot accept their own invitation. If the stored email in a client-bound card "
        "differs from the accepting account email, the card keeps the master's stored email, the master-client link "
        "is marked with `invite_email_mismatch`, and an in-app notification is created for the master."
    ),
    response_model=InvitationAcceptOut,
    response_description=(
        "Client id linked by the invitation, plus a flag showing whether the accepting account email differed from "
        "the email stored in the master's client card."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorDetail,
            "description": "Session missing or invalid.",
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorDetail,
            "description": (
                "Email is not verified, or the current user owns the master profile that created the invite."
            ),
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorDetail,
            "description": (
                "Invitation token does not exist, or the target client card is no longer linked to the master."
            ),
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorDetail,
            "description": (
                "The invitation was already accepted, the client card is linked to another account, or this user is "
                "already linked to the same master through another client card."
            ),
        },
        status.HTTP_410_GONE: {
            "model": ErrorDetail,
            "description": "The invitation was revoked or its expiration time has passed.",
        },
    },
)
async def post_accept_invitation(
    token: str,
    payload: InvitationAccept,
    use_case: Annotated[AcceptInvitationUseCase, Depends(get_accept_invitation_use_case)],
    user: Annotated[User, Depends(require_user)],
) -> InvitationAcceptOut:
    try:
        client_id, mismatch = await use_case(
            token=token,
            display_name=payload.display_name,
            phone=payload.phone,
            user=user,
        )
        return InvitationAcceptOut(client_id=client_id, email_mismatch_with_master_record=mismatch)
    except AcceptInvitationError as error:
        status_code = error.status_code if error.status_code else status.HTTP_400_BAD_REQUEST
        error_message = error.error_message if error.error_message else "Invitation not accepted."
        raise HTTPException(status_code=status_code, detail=error_message) from None
