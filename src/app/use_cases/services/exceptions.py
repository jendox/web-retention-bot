class ServiceNotFoundError(Exception):
    """Service missing or not owned by this master."""


class ServiceHasBookingsError(Exception):
    """Cannot remove a service that already has bookings."""
