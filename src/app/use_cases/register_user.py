from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.security import hash_password
from app.core.structured_logging import get_logger, log_context
from app.repositories.users import UserRepository, get_user_repo
from app.schemas.auth import RegisterPayload
from app.schemas.user import UserSchema

logger = get_logger("app.register_user")


class UserAlreadyExists(Exception): ...


class RegisterUserUseCase:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def register_client(self, *, email: str, password: str) -> UserSchema:
        email_norm = email.strip().lower()
        with log_context(use_case="register_client", email=email_norm):
            existing = await self.user_repo.get_by_email(email_norm)
            if existing is not None:
                logger.info("failed", reason="user_already_exists", user_id=str(existing.id))
                raise UserAlreadyExists("Email already registered")
            user = await self.user_repo.create(
                email=email_norm,
                password_hash=hash_password(password),
            )
            logger.info("success", user_id=str(user.id))
            return UserSchema.from_model(user)

    async def __call__(self, payload: RegisterPayload) -> UserSchema:
        email = str(payload.email).lower()
        with log_context(use_case="register_master_user", email=email):
            user = await self.user_repo.get_by_email(email)
            if user is not None:
                logger.info("failed", reason="user_already_exists", user_id=str(user.id))
                raise UserAlreadyExists("Email already registered")

            user = await self.user_repo.create(
                email=email,
                password_hash=hash_password(payload.password),
            )
            logger.info("success", user_id=str(user.id))
            return UserSchema.from_model(user)


def get_register_user_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> RegisterUserUseCase:
    return RegisterUserUseCase(user_repo)
