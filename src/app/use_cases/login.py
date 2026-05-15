from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends

from app.core.security import verify_password
from app.repositories.users import UserRepository, get_user_repo
from app.schemas.user import UserSchema

__all__ = [
    "EmailNotVerifiedError",
    "InactiveUserError",
    "InvalidCredentialsError",
    "LoginUseCase",
    "get_login_use_case",
]

logger = logging.getLogger("app.login")


class InvalidCredentialsError(Exception): ...


class EmailNotVerifiedError(Exception): ...


class InactiveUserError(Exception): ...


class LoginUseCase:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def __call__(self, *, email: str, password: str) -> UserSchema:
        email = str(email).lower()
        user = await self.user_repo.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            logger.info(
                "login_failed",
                extra={"reason": "invalid_credentials", "email": email},
            )
            raise InvalidCredentialsError()

        if user.email_verified_at is None:
            logger.info(
                "login_failed",
                extra={"reason": "email_not_verified", "email": email},
            )
            raise EmailNotVerifiedError()

        if not user.is_active:
            logger.info(
                "login_failed",
                extra={"reason": "inactive_user", "email": email},
            )
            raise InactiveUserError()

        return UserSchema.from_model(user)


def get_login_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> LoginUseCase:
    return LoginUseCase(user_repo)
