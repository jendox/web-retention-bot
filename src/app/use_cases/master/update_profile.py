from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.api.deps import require_master_profile
from app.core.structured_logging import get_logger
from app.models import MasterProfile
from app.repositories.masters import MasterRepository, get_master_repo
from app.schemas.master import MasterProfileSchema, MasterProfileUpdate
from app.use_cases.master.exceptions import MasterProfileEmptyPatchError, MasterProfileNoFieldsToUpdateError

__all__ = ["UpdateMasterProfileUseCase", "get_update_master_profile_use_case"]

logger = get_logger("app.master")


class UpdateMasterProfileUseCase:
    def __init__(
        self,
        master_profile: MasterProfile,
        master_repo: MasterRepository,
    ) -> None:
        self._master_profile = master_profile
        self._master_repo = master_repo

    async def __call__(self, payload: MasterProfileUpdate) -> MasterProfileSchema:
        patch = payload.model_dump(exclude_unset=True)
        if not patch:
            logger.warning("failed", reason="empty_patch")
            raise MasterProfileEmptyPatchError()

        changed = self._master_profile.apply_patch(patch)
        if not changed:
            logger.warning("failed", reason="nothing_changed")
            raise MasterProfileNoFieldsToUpdateError()

        await self._master_repo.flush()

        return MasterProfileSchema.model_validate(self._master_profile)


def get_update_master_profile_use_case(
    master_profile: Annotated[MasterProfile, Depends(require_master_profile)],
    master_repo: Annotated[MasterRepository, Depends(get_master_repo)],
) -> UpdateMasterProfileUseCase:
    return UpdateMasterProfileUseCase(master_profile, master_repo)
