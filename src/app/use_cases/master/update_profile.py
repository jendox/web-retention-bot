from typing import Annotated, Any

from fastapi import Depends

from app.api.deps import require_master_profile
from app.core.structured_logging import get_logger
from app.models import MasterProfile
from app.repositories.masters import MasterRepository, get_master_repo
from app.schemas.master import MasterProfileSchema, MasterProfileUpdate

__all__ = [
    "UpdateMasterProfileUseCase",
    "get_update_master_profile_use_case",
]

logger = get_logger("app.master")

_NOT_NULLABLE_FIELDS = frozenset({
    "display_name",
    "timezone",
    "default_currency",
})


class UpdateMasterProfileUseCase:
    def __init__(
        self,
        master_profile: MasterProfile,
        master_repo: MasterRepository,
    ) -> None:
        self._master_profile = master_profile
        self._master_repo = master_repo

    def _apply_patch_updates(self, patch: dict[str, Any]) -> None:
        for key, value in patch.items():
            if key in _NOT_NULLABLE_FIELDS and value is None:
                continue
            setattr(self._master_profile, key, value)

    async def __call__(self, payload: MasterProfileUpdate) -> MasterProfileSchema:
        patch = payload.model_dump(exclude_unset=True)
        if not patch:
            logger.warning("failed", reason="empty_patch")
        else:
            self._apply_patch_updates(patch)
            await self._master_repo.flush()

        return MasterProfileSchema.model_validate(self._master_profile)


def get_update_master_profile_use_case(
    master_profile: Annotated[MasterProfile, Depends(require_master_profile)],
    master_repo: Annotated[MasterRepository, Depends(get_master_repo)],
) -> UpdateMasterProfileUseCase:
    return UpdateMasterProfileUseCase(master_profile, master_repo)
