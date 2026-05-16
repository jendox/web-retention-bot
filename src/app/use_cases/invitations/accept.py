from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, status

from app.core.structured_logging import get_logger, log_context
from app.models import Invitation, MasterProfile
from app.models.client import InvitationStatus
from app.models.user import User
from app.repositories.clients import ClientRepository, get_client_repo
from app.repositories.invitations import InvitationRepository, get_invitation_repo
from app.services.notifications.dispatcher import NotificationDispatcher, get_notification_dispatcher
from app.use_cases.invitations.exceptions import AcceptInvitationError

__all__ = [
    "AcceptInvitationUseCase",
    "get_accept_invitation_use_case",
]

logger = get_logger("app.invitation")


class AcceptInvitationUseCase:
    def __init__(
        self,
        client_repo: ClientRepository,
        invite_repo: InvitationRepository,
        dispatcher: NotificationDispatcher,
    ) -> None:
        self._client_repo = client_repo
        self._invite_repo = invite_repo
        self._dispatcher = dispatcher

    @staticmethod
    def _check_invite(invite: Invitation | None) -> Invitation:
        if not invite:
            logger.error("failed", reason="invitation_not_found")
            raise AcceptInvitationError(
                status_code=status.HTTP_404_NOT_FOUND, error_message="Invitation not found",
            )
        if invite.revoked_at is not None:
            logger.warning("failed", reason="invitation_revoked")
            raise AcceptInvitationError(
                status_code=status.HTTP_410_GONE, error_message="Invitation revoked",
            )
        if invite.accepted_at is not None:
            logger.warning("failed", reason="invitation_already_accepted")
            raise AcceptInvitationError(
                status_code=status.HTTP_409_CONFLICT, error_message="Invitation already accepted",
            )
        if invite.expires_at < datetime.now(UTC):
            logger.warning("failed", reason="invitation_expired")
            raise AcceptInvitationError(
                status_code=status.HTTP_410_GONE, error_message="Invitation expired",
            )
        return invite

    async def _accept_targeted_invite(
        self,
        *,
        invite: Invitation,
        user_id: UUID,
        user_email: str,
        master_profile: MasterProfile,
        display_name: str,
        phone: str | None,
    ) -> tuple[UUID, bool]:
        row = await self._client_repo.get_link_with_client(
            master_id=invite.master_id, client_id=invite.target_client_id,
        )
        if row is None:
            logger.error(
                "failed",
                reason="target_client_not_found",
                target_client_id=str(invite.target_client_id) if invite.target_client_id else None,
            )
            raise AcceptInvitationError(
                status_code=status.HTTP_404_NOT_FOUND, error_message="Client not found.",
            ) from None

        link, client = row
        if invite.target_client_id != client.id:
            logger.warning(
                "failed",
                reason="invitation_client_mismatch",
                target_client_id=str(invite.target_client_id) if invite.target_client_id else None,
                client_id=str(client.id),
            )
            raise AcceptInvitationError(
                status_code=status.HTTP_400_BAD_REQUEST, error_message="Invitation client mismatch.",
            ) from None

        if client.user_id is not None and client.user_id != user_id:
            logger.warning(
                "failed",
                reason="client_already_linked_to_another_account",
                target_client_id=str(invite.target_client_id) if invite.target_client_id else None,
                client_user_id=str(client.user_id),
            )
            raise AcceptInvitationError(
                status_code=status.HTTP_409_CONFLICT,
                error_message="This client card is already linked to another account.",
            ) from None

        stored_profile_email = client.email.strip().lower() if client.email else None

        client.display_name = display_name
        client.phone = phone
        client.user_id = user_id

        link.linked_account_email = user_email
        email_mismatch = False

        if stored_profile_email and stored_profile_email != user_email:
            email_mismatch = True
            link.invite_email_mismatch = True
            await self._dispatcher.dispatch_invite_email_mismatch_for_master(
                master_user_id=master_profile.user_id,
                master_profile_id=master_profile.id,
                client_id=client.id,
                profile_email=stored_profile_email,
                account_email=user_email,
                client_display_name=client.display_name,
            )
        else:
            link.invite_email_mismatch = False
            client.email = user_email

        return client.id, email_mismatch

    async def _accept_open_invite(
        self,
        *,
        invite: Invitation,
        user_id: UUID,
        user_email: str,
        display_name: str,
        phone: str | None,
    ) -> UUID:
        existing = await self._client_repo.client_ids_for_master_user(invite.master_id, user_id)
        if existing:
            logger.warning("failed", reason="already_linked_to_master")
            raise AcceptInvitationError(
                status_code=status.HTTP_409_CONFLICT,
                error_message="You are already linked to this master.",
            ) from None

        client = await self._client_repo.create(
            display_name=display_name,
            phone=phone,
            email=user_email,
        )
        client.user_id = user_id

        link = await self._client_repo.create_link(
            master_id=invite.master_id,
            client_id=client.id,
            invitation_status=InvitationStatus.LINKED,
        )
        link.linked_account_email = user_email
        link.invite_email_mismatch = False

        return client.id

    async def __call__(
        self,
        *,
        token: str,
        display_name: str,
        phone: str | None,
        user: User,
    ) -> tuple[UUID, bool]:
        invite = await self._invite_repo.get_by_token(token)

        with log_context(
            use_case="accept_invitation",
            invitation_id=str(invite.id) if invite is not None else None,
            master_id=str(invite.master_id) if invite is not None else None,
            user_id=str(user.id),
        ):
            invite = self._check_invite(invite)

            master_profile = invite.master
            if master_profile.user_id == user.id:
                logger.warning("failed", reason="master_trying_to_link_himself")
                raise AcceptInvitationError(
                    status_code=status.HTTP_403_FORBIDDEN,
                    error_message="You cannot accept your own invitation.",
                )

            account_email = user.email.strip().lower()
            email_mismatch = False

            display_name = display_name.strip()
            phone = phone.strip() if phone and phone.strip() else None

            if invite.target_client_id is not None:
                client_id, email_mismatch = await self._accept_targeted_invite(
                    invite=invite,
                    user_id=user.id,
                    user_email=account_email,
                    master_profile=master_profile,
                    display_name=display_name,
                    phone=phone,
                )
            else:
                client_id = await self._accept_open_invite(
                    invite=invite,
                    user_id=user.id,
                    user_email=account_email,
                    display_name=display_name,
                    phone=phone,
                )

            invite.linked_client_id = client_id
            invite.accepted_at = datetime.now(UTC)

            logger.info(
                "success",
                target_client_id=str(invite.target_client_id) if invite.target_client_id else None,
                linked_client_id=str(client_id),
                email_mismatch=email_mismatch,
            )

            return client_id, email_mismatch


def get_accept_invitation_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
    invite_repo: Annotated[InvitationRepository, Depends(get_invitation_repo)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> AcceptInvitationUseCase:
    return AcceptInvitationUseCase(client_repo, invite_repo, dispatcher)
