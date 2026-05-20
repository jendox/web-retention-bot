"""Client use case exceptions."""

from fastapi import status


class ClientNotFoundError(Exception):
    """No client for this master or client id does not exist."""


class ClientNothingToUpdateError(Exception):
    """PATCH body contained no fields to apply."""


class ClientEmailLockedError(Exception):
    """Email is controlled by the linked client account and cannot be changed."""


class ClientNameLockedError(Exception):
    """Display name is controlled by the linked client account and cannot be changed."""


class ClientHasBlockingRelationsError(Exception):
    """Client cannot be removed (e.g. has bookings or invitations)."""

    def __init__(self, *, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ClientMasterLinkError(Exception):
    status_code = status.HTTP_404_NOT_FOUND
    error_message = "Not linked to this master"
