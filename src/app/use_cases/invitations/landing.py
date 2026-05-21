from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models import Invitation
from app.repositories.invitations import InvitationRepository, get_invitation_repo
from app.repositories.services import ServiceRepository, get_service_repo
from app.schemas.invitation import InvitationLandingResponse
from app.schemas.service import ServiceSchema
from app.use_cases.invitations.exceptions import (
    InvitationExpiredError,
    InvitationNotFoundError,
    InvitationRevokedError,
)

__all__ = ["InvitationLandingUseCase", "get_invitation_landing_use_case"]

logger = get_logger("app.invitation")


class InvitationLandingUseCase:
    def __init__(
        self,
        service_repo: ServiceRepository,
        invite_repo: InvitationRepository,
    ) -> None:
        self._service_repo = service_repo
        self._invite_repo = invite_repo

    @staticmethod
    def _check_invite(invite: Invitation | None) -> Invitation:
        if not invite:
            logger.error("failed", reason="invitation_not_found")
            raise InvitationNotFoundError()
        if invite.revoked_at is not None:
            logger.warning("failed", reason="invitation_revoked")
            raise InvitationRevokedError()
        if invite.expires_at < datetime.now(UTC):
            logger.warning("failed", reason="invitation_expired")
            raise InvitationExpiredError()
        return invite

    async def __call__(
        self,
        *,
        token: str,
    ) -> InvitationLandingResponse:
        invite = await self._invite_repo.get_by_token(token)

        with log_context(
            use_case="invitation_landing",
            invitation_id=str(invite.id) if invite is not None else None,
            master_id=str(invite.master_id) if invite is not None else None,
            client_id=str(invite.linked_client_id) if invite is not None else None,
        ):
            invite = self._check_invite(invite)

            master_profile = invite.master
            target = invite.target_client
            invite_kind: Literal["open", "client"] = "client" if invite.target_client_id else "open"
            master_record_has_email = bool(target and target.email and target.email.strip())

            svc_list_raw = await self._service_repo.list_for_master(master_profile.id)
            services_public = [
                ServiceSchema.model_validate(service)
                for service in svc_list_raw
                if service.is_active
            ]
            return InvitationLandingResponse(
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


def get_invitation_landing_use_case(
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    invite_repo: Annotated[InvitationRepository, Depends(get_invitation_repo)],
) -> InvitationLandingUseCase:
    return InvitationLandingUseCase(service_repo, invite_repo)
