from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.security import hash_password
from app.repositories.users import UserRepository, get_user_repo
from app.schemas.auth import RegisterPayload
from app.schemas.user import UserSchema


class UserAlreadyExists(Exception): ...


class RegisterUserUseCase:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def __call__(self, payload: RegisterPayload) -> UserSchema:
        email = str(payload.email).lower()
        user = await self.user_repo.get_by_email(email)
        if user is not None:
            raise UserAlreadyExists("Email already registered")

        user = await self.user_repo.create(
            email=email,
            password_hash=hash_password(payload.password),
        )
        return UserSchema.from_model(user)


def get_register_user_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> RegisterUserUseCase:
    return RegisterUserUseCase(user_repo)
