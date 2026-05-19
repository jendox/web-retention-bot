class BookingsError(Exception):
    def __init__(
        self,
        *,
        status_code: int | None = None,
        error_message: str | None = None,
    ) -> None:
        super().__init__(error_message)
        if status_code is not None:
            self.status_code = status_code
        if error_message is not None:
            self.error_message = error_message


class AvailabilitySlotsError(BookingsError): ...


class CreateBookingError(BookingsError): ...


class UpdateBookingError(BookingsError): ...
