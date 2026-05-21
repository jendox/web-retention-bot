from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.security import hash_password, verify_password
from app.core.structured_logging import get_logger, log_context
from app.models.user import User
from app.repositories.users import UserRepository, get_user_repo
from app.use_cases.auth.exceptions import InvalidCurrentPasswordError

__all__ = ["ChangePasswordUseCase", "get_change_password_use_case"]

logger = get_logger("app.change_password")


class ChangePasswordUseCase:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def __call__(self, *, user: User, current_password: str, new_password: str) -> None:
        with log_context(use_case="change_password", user_id=str(user.id)):
            if not verify_password(current_password, user.password_hash):
                logger.info("failed", reason="invalid_current_password")
                raise InvalidCurrentPasswordError()
            user.password_hash = hash_password(new_password)
            logger.info("success")


def get_change_password_use_case(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> ChangePasswordUseCase:
    return ChangePasswordUseCase(user_repo)
