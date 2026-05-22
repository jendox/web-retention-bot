from app.core.exceptions import ConflictError, DomainError, NotFoundError, ValidationError

__all__ = [
    "ClientError",
    "ClientNotFoundError",
    "ClientProfileNotFoundError",
    "ClientNothingToUpdateError",
    "ClientEmailLockedError",
    "ClientNameLockedError",
    "ClientHasBookingsError",
    "ClientHasInvitationError",
    "ClientMasterLinkNotFoundError",
]


class ClientError(DomainError):
    """Base clients use case error."""


class ClientNotFoundError(ClientError, NotFoundError):
    code = "clients.not_found"
    message = "Client not found."


class ClientProfileNotFoundError(ClientError, NotFoundError):
    code = "clients.profile_not_found"
    message = "Client profile not found"


class ClientNothingToUpdateError(ClientError, ValidationError):
    code = "clients.empty_patch"
    message = "No fields to update."


class ClientEmailLockedError(ClientError, ConflictError):
    code = "clients.email_locked"
    message = "Client email is linked to the client account and cannot be changed."


class ClientNameLockedError(ClientError, ConflictError):
    code = "clients.name_locked"
    message = "Client name is linked to the client account and cannot be changed."


class ClientHasBookingsError(ClientError, ConflictError):
    code = "clients.has_bookings"
    message = "Client has bookings and cannot be deleted."


class ClientHasInvitationError(ClientError, ConflictError):
    code = "clients.has_invitation"
    message = "Client is linked to an invitation and cannot be deleted."


class ClientMasterLinkNotFoundError(ClientError, NotFoundError):
    code = "clients.master_link_not_found"
    message = "Not linked to this master"
