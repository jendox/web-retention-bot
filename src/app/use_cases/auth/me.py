from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.structured_logging import get_logger, log_context
from app.models.user import User
from app.repositories.clients import ClientRepository, get_client_repo
from app.schemas.user import UserMeOut, UserSchema

__all__ = ["MeUseCase", "get_me_use_case"]

logger = get_logger("app.me")


class MeUseCase:
    def __init__(self, client_repo: ClientRepository) -> None:
        self._client_repo = client_repo

    async def __call__(self, *, user: User) -> UserMeOut:
        with log_context(use_case="me", user_id=str(user.id)):
            base_user = UserSchema.model_validate(user)
            client = await self._client_repo.primary_client_profile_for_user(user.id)
            return UserMeOut(
                **base_user.model_dump(),
                client_display_name=client.display_name if client else None,
                client_phone=client.phone if client else None,
            )


def get_me_use_case(
    client_repo: Annotated[ClientRepository, Depends(get_client_repo)],
) -> MeUseCase:
    return MeUseCase(client_repo)
