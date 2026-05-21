from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.password_reset_token import PasswordResetTokenError, parse_password_reset_token
from app.core.security import hash_password
from app.core.structured_logging import get_logger, log_context
from app.repositories.users import UserRepository, get_user_repo
from app.use_cases.auth.exceptions import InvalidPasswordResetTokenError

__all__ = ["ResetPasswordUseCase", "get_reset_password_use_case"]


logger = get_logger("app.reset_password")


class ResetPasswordUseCase:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def __call__(self, *, secret: str, token: str, new_password: str) -> None:
        try:
            user_id, email_snap = parse_password_reset_token(secret=secret, token=token.strip())

            with log_context(use_case="reset_password", user_id=str(user_id)):
                user = await self._user_repo.get_by_id(user_id)
                if user is None or user.email != email_snap:
                    logger.warning("failed", reason="user_missing_or_email_mismatch")
                    raise InvalidPasswordResetTokenError("User missing or email mismatch")

                user.password_hash = hash_password(new_password)
                logger.info("success")
        except PasswordResetTokenError as error:
            raise InvalidPasswordResetTokenError() from error


def get_reset_password_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> ResetPasswordUseCase:
    return ResetPasswordUseCase(user_repo)
