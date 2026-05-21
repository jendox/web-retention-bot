from app.core.exceptions import ConflictError, DomainError, ForbiddenError, UnauthorizedError, ValidationError


class AuthError(DomainError):
    """Base auth use case error."""


class UserAlreadyExistsError(AuthError, ConflictError):
    code = "auth.user_already_exists"
    message = "User already exists."


class InvalidCredentialsError(AuthError, UnauthorizedError):
    code = "auth.invalid_credentials"
    message = "Invalid credentials."


class EmailNotVerifiedError(AuthError, ForbiddenError):
    code = "auth.email_not_verified"
    message = "Email address is not verified yet."


class InactiveUserError(AuthError, ForbiddenError):
    code = "auth.inactive_user"
    message = "Account is disabled."


class InvalidCurrentPasswordError(AuthError, ValidationError):
    code = "auth.invalid_current_password"
    message = "Current password is incorrect."


class InvalidEmailVerificationTokenError(AuthError, ValidationError):
    code = "auth.invalid_email_verification_token"
    message = "Invalid or expired verification link"


class InvalidPasswordResetTokenError(AuthError, ValidationError):
    code = "auth.invalid_password_reset_token"
    message = "Invalid password reset token."
