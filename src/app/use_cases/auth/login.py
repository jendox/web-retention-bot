from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.security import verify_password
from app.core.structured_logging import get_logger, log_context
from app.repositories.users import UserRepository, get_user_repo
from app.schemas.user import UserSchema
from app.use_cases.auth.exceptions import EmailNotVerifiedError, InactiveUserError, InvalidCredentialsError

__all__ = ["LoginUseCase", "get_login_use_case"]


logger = get_logger("app.login")


class LoginUseCase:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def __call__(self, *, email: str, password: str) -> UserSchema:
        email = str(email).lower()
        with log_context(use_case="login", email=email):
            user = await self.user_repo.get_by_email(email)
            if user is None or not verify_password(password, user.password_hash):
                logger.info("failed", reason="invalid_credentials")
                raise InvalidCredentialsError()

            if user.email_verified_at is None:
                logger.info("failed", reason="email_not_verified", user_id=str(user.id))
                raise EmailNotVerifiedError()

            if not user.is_active:
                logger.info("failed", reason="inactive_user", user_id=str(user.id))
                raise InactiveUserError()

            logger.info("success", user_id=str(user.id))
            return UserSchema.model_validate(user)


def get_login_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> LoginUseCase:
    return LoginUseCase(user_repo)
