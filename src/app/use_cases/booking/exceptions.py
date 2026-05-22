from app.core.exceptions import ConflictError, DomainError, ForbiddenError, NotFoundError, ValidationError

__all__ = [
    "BookingError",
    "AvailabilitySlotsError",
    "AvailabilityMasterNotFoundError",
    "AvailabilityServiceNotFoundError",
    "AvailabilityDateInPastError",
    "AvailabilityDateOutsideHorizonError",
    "BookingServiceNotFoundError",
    "BookingMasterNotFoundError",
    "BookingClientLinkNotFoundError",
    "BookingUnknownClientLinkageError",
    "BookingNotLinkedToMasterError",
    "BookingRequestedSlotUnavailableError",
    "BookingOverlapsExistingError",
    "BookingNotFoundError",
    "ActiveBookingNotFoundError",
    "BookingAttendanceNotPendingError",
]


class BookingError(DomainError):
    """Base booking use case error."""


class AvailabilitySlotsError(BookingError):
    """Base error for available slots calculation."""


class AvailabilityMasterNotFoundError(AvailabilitySlotsError, NotFoundError):
    code = "availability.master_not_found"
    message = "Master not found"


class AvailabilityServiceNotFoundError(AvailabilitySlotsError, NotFoundError):
    code = "availability.service_not_found"
    message = "Service not found or not available"


class AvailabilityDateInPastError(AvailabilitySlotsError, ValidationError):
    code = "availability.date_in_past"
    message = "Date is in the past"


class AvailabilityDateOutsideHorizonError(AvailabilitySlotsError, ValidationError):
    code = "availability.date_outside_horizon"
    message = "Date is outside booking horizon"


class BookingServiceNotFoundError(BookingError, NotFoundError):
    code = "booking.service_not_found"
    message = "Service not found"


class BookingMasterNotFoundError(BookingError, NotFoundError):
    code = "booking.master_not_found"
    message = "Master not found"


class BookingClientLinkNotFoundError(BookingError, NotFoundError):
    code = "booking.client_link_not_found"
    message = "Client link not found"


class BookingUnknownClientLinkageError(BookingError, ValidationError):
    code = "booking.unknown_client_linkage"
    message = "Unknown client linkage"


class BookingNotLinkedToMasterError(BookingError, ForbiddenError):
    code = "booking.not_linked_to_master"
    message = "Not linked to this master"


class BookingRequestedSlotUnavailableError(BookingError, ValidationError):
    code = "booking.requested_slot_unavailable"
    message = "Requested slot unavailable"


class BookingOverlapsExistingError(BookingError, ConflictError):
    code = "booking.overlapping_exists"
    message = "Overlapping booking exists"


class BookingNotFoundError(BookingError, NotFoundError):
    code = "booking.not_found"
    message = "Booking not found"


class ActiveBookingNotFoundError(BookingError, NotFoundError):
    code = "booking.active_not_found"
    message = "Active booking not found"


class BookingAttendanceNotPendingError(BookingError, ValidationError):
    code = "booking.attendance_not_pending"
    message = "Attendance already marked or booking is not awaiting confirmation"
