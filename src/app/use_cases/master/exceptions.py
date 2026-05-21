from app.core.exceptions import DomainError, ValidationError

__all__ = [
    "MasterProfileError",
    "MasterProfileEmptyPatchError",
    "MasterProfileNoFieldsToUpdateError",
]


class MasterProfileError(DomainError):
    """Base master profile error."""


class MasterProfileEmptyPatchError(MasterProfileError, ValidationError):
    code = "master_profile.empty_patch"
    message = "No fields to update."


class MasterProfileNoFieldsToUpdateError(MasterProfileError, ValidationError):
    code = "master_profile.no_fields_to_update"
    message = "No fields to update."
