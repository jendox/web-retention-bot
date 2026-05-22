from app.core.exceptions import ConflictError, DomainError, NotFoundError, ValidationError

__all__ = [
    "ServiceError",
    "ServiceNotFoundError",
    "ServiceHasBookingsError",
    "ServiceEmptyPatchError",
    "ServiceNoFieldsToUpdateError",
]


class ServiceError(DomainError):
    """Base services use case error."""


class ServiceNotFoundError(ServiceError, NotFoundError):
    code = "services.not_found"
    message = "Service not found."


class ServiceHasBookingsError(ServiceError, ConflictError):
    code = "services.has_bookings"
    message = "Service has bookings and cannot be deleted."


class ServiceEmptyPatchError(ServiceError, ValidationError):
    code = "services.empty_patch"
    message = "No fields to update."


class ServiceNoFieldsToUpdateError(ServiceError, ValidationError):
    code = "services.no_fields_to_update"
    message = "No fields to update."
