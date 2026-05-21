from app.core.exceptions import ConflictError, DomainError, ForbiddenError, NotFoundError, ValidationError

__all__ = [
    "InvitationError",
    "InvitationNotFoundError",
    "InvitationRevokedError",
    "InvitationExpiredError",
    "InvitationAlreadyAcceptedError",
    "InvitationClientNotFoundError",
    "InvitationClientMismatchError",
    "InvitationClientAlreadyLinkedError",
    "InvitationAlreadyLinkedToMasterError",
    "InvitationOwnAccountError",
    "InvitationClientLoginAlreadyLinkedError",
    "InvitationActiveAlreadyExistsError",
]


class InvitationError(DomainError):
    """Base invitation use case error."""


class InvitationNotFoundError(InvitationError, NotFoundError):
    code = "invitations.not_found"
    message = "Invitation not found"


class InvitationRevokedError(InvitationError, ValidationError):
    code = "invitations.revoked"
    message = "Invitation revoked"


class InvitationExpiredError(InvitationError, ValidationError):
    code = "invitations.expired"
    message = "Invitation expired"


class InvitationAlreadyAcceptedError(InvitationError, ConflictError):
    code = "invitations.already_accepted"
    message = "Invitation already accepted"


class InvitationClientNotFoundError(InvitationError, NotFoundError):
    code = "invitations.client_not_found"
    message = "Client not found."


class InvitationClientMismatchError(InvitationError, ValidationError):
    code = "invitations.client_mismatch"
    message = "Invitation client mismatch."


class InvitationClientAlreadyLinkedError(InvitationError, ConflictError):
    code = "invitations.client_already_linked"
    message = "This client card is already linked to another account."


class InvitationAlreadyLinkedToMasterError(InvitationError, ConflictError):
    code = "invitations.already_linked_to_master"
    message = "You are already linked to this master."


class InvitationOwnAccountError(InvitationError, ForbiddenError):
    code = "invitations.own_account"
    message = "You cannot accept your own invitation."


class InvitationClientLoginAlreadyLinkedError(InvitationError, ConflictError):
    code = "invitations.client_login_already_linked"
    message = "Client already has a login linked."


class InvitationActiveAlreadyExistsError(InvitationError, ConflictError):
    code = "invitations.active_already_exists"
    message = "An active invitation already exists for this client."
