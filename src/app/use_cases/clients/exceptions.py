"""Client use case exceptions."""


class ClientNotFoundError(Exception):
    """No client for this master or client id does not exist."""


class ClientNothingToUpdateError(Exception):
    """PATCH body contained no fields to apply."""


class ClientHasBlockingRelationsError(Exception):
    """Client cannot be removed (e.g. has bookings or invitations)."""

    def __init__(self, *, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
