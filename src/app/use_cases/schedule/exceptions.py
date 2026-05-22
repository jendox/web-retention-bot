from app.core.exceptions import ConflictError, DomainError

__all__ = [
    "ScheduleError",
    "ScheduleBookingConflictError",
]


class ScheduleError(DomainError):
    """Base schedule use case error."""


class ScheduleBookingConflictError(ScheduleError, ConflictError):
    code = "schedule.booking_conflict"
    message = "Schedule changes affect existing bookings."
