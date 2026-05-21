from __future__ import annotations

from typing import Annotated
from urllib.parse import quote

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.password_reset_token import mint_password_reset_token
from app.core.structured_logging import get_logger, log_context
from app.repositories.users import UserRepository, get_user_repo
from app.services.notifications.email_send import send_multipart_email
from app.services.notifications.mail_render import render_password_reset

__all__ = ["ForgotPasswordUseCase", "get_forgot_password_use_case"]

logger = get_logger("app.forgot_password")


class ForgotPasswordUseCase:
    def __init__(self, user_repo: UserRepository, settings: Settings) -> None:
        self._user_repo = user_repo
        self._settings = settings

    async def __call__(self, *, email: str) -> None:
        email_norm = email.strip().lower()
        with log_context(use_case="forgot_password", email=email_norm):
            user = await self._user_repo.get_by_email(email_norm)
            if user is None or user.email_verified_at is None:
                logger.info("skipped", reason="user_not_found_or_unverified")
                return

            token = mint_password_reset_token(
                secret=self._settings.security.secret_key,
                user_id=user.id,
                email=user.email,
                ttl_seconds=self._settings.security.password_reset_ttl_seconds,
            )
            reset_url = (
                f"{self._settings.security.frontend_public_origin.rstrip('/')}"
                f"/reset-password?token={quote(token, safe='')}"
            )

            if self._settings.security.auth_log_verification_link:
                logger.info("password_reset.log_link", to_email=email_norm, reset_url=reset_url)

            subject, text_body, html_body = render_password_reset(
                reset_url=reset_url,
                recipient_email=email_norm,
            )
            await send_multipart_email(
                settings=self._settings,
                to_email=email_norm,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                log_sent_event="email.password_reset.sent",
            )
            logger.info("sent", to_email=email_norm)


def get_forgot_password_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> ForgotPasswordUseCase:
    return ForgotPasswordUseCase(user_repo, get_settings())
