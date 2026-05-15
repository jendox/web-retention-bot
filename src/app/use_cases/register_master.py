from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.repositories.masters import MasterRepository, get_master_repo
from app.schemas.master import MasterProfileSchema
from app.schemas.user import UserSchema

__all__ = [
    "RegisterMasterUseCase",
    "get_register_master_use_case",
]


class RegisterMasterUseCase:
    def __init__(self, master_repo: MasterRepository) -> None:
        self.master_repo = master_repo

    async def __call__(self, user: UserSchema, display_name: str) -> MasterProfileSchema:
        master = await self.master_repo.get_by_user_id(user_id=user.id)
        if master is None:
            master = await self.master_repo.create(
                user_id=user.id,
                display_name=display_name,
            )

        return MasterProfileSchema.from_model(master)


def get_register_master_use_case(
    master_repo: Annotated[MasterRepository, Depends(get_master_repo)],
) -> RegisterMasterUseCase:
    return RegisterMasterUseCase(master_repo)
