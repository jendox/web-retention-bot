class AppError(Exception):
    code: str = "app.error"
    message: str = "Application Error"

    def __init__(
        self,
        message: str | None = None,
        *,
        context: dict[str, object] | None = None,
    ) -> None:
        self.message = message or self.message
        self.context = context or {}
        super().__init__(self.message)


class DomainError(AppError): ...


class ApplicationError(AppError): ...


class NotFoundError(DomainError): ...


class ConflictError(DomainError): ...


class ValidationError(DomainError): ...


class ForbiddenError(DomainError): ...


class UnauthorizedError(DomainError): ...
