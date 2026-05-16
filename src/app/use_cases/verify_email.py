from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.core.verification_token import EmailVerificationTokenError, parse_email_verification_token
from app.repositories.users import UserRepository, get_user_repo
from app.schemas.user import UserSchema

__all__ = [
    "VerifyEmailUseCase",
    "get_verify_email_use_case",
]

logger = get_logger("app.verify_email")


class VerifyEmailUseCase:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def __call__(self, *, secret: str, token: str) -> UserSchema:
        user_id, email_snap = parse_email_verification_token(secret=secret, token=token.strip())

        with log_context(use_case="verify_email", user_id=str(user_id), email=email_snap):
            user = await self._user_repo.get_by_id(user_id)
            if user is None or user.email != email_snap:
                logger.warning("failed", reason="user_missing_or_email_mismatch")
                raise EmailVerificationTokenError()

            if user.email_verified_at is None:
                user.email_verified_at = datetime.now(UTC)
                logger.info("verified")
            else:
                logger.info("already_verified")

            return UserSchema.from_model(user)


def get_verify_email_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)]
) -> VerifyEmailUseCase:
    return VerifyEmailUseCase(user_repo)
