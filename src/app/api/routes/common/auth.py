from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import require_user
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordPayload,
    ForgotPasswordPayload,
    LoginPayload,
    RegisterAcceptedOut,
    RegisterClientPayload,
    RegisterMasterPayload,
    ResetPasswordPayload,
    VerifyEmailPayload,
)
from app.schemas.errors import ErrorDetail
from app.schemas.user import UserMeOut, UserSchema
from app.services.sessions import SessionManager, get_session_manager
from app.use_cases.auth import (
    ChangePasswordUseCase,
    ForgotPasswordUseCase,
    LoginUseCase,
    MeUseCase,
    RegisterClientAccountUseCase,
    RegisterMasterAccountUseCase,
    ResetPasswordUseCase,
    VerifyEmailUseCase,
    get_change_password_use_case,
    get_forgot_password_use_case,
    get_login_use_case,
    get_me_use_case,
    get_register_client_account_use_case,
    get_register_master_account_use_case,
    get_reset_password_use_case,
    get_verify_email_use_case,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    path="/csrf",
    summary="Issue a CSRF token",
    description=(
        "Sets a readable CSRF cookie and returns the same token in the response body. The SPA should call this "
        "before unsafe requests (`POST`, `PUT`, `PATCH`, `DELETE`) and then send the token in `X-CSRF-Token`."
    ),
    response_description="CSRF token issued.",
)
async def csrf_token(
    response: Response,
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
) -> dict[str, str]:
    token = session_manager.set_csrf_cookie(response)
    return {"csrf_token": token}


@router.post(
    path="/register-master",
    summary="Register a master account",
    description=(
        "Creates a user and linked master profile, sends a verification email, and returns public "
        "identifiers. No session cookie is issued until `/auth/verify-email` succeeds."
    ),
    response_model=RegisterAcceptedOut,
    status_code=status.HTTP_201_CREATED,
    response_description="User and master profile created; confirm email before login.",
    responses={
        status.HTTP_409_CONFLICT: {
            "model": ErrorDetail,
            "description": "This email is already registered.",
        },
    },
)
async def register_master(
    payload: RegisterMasterPayload,
    use_case: Annotated[RegisterMasterAccountUseCase, Depends(get_register_master_account_use_case)],
) -> RegisterAcceptedOut:
    return await use_case(payload)


@router.post(
    path="/register-client",
    summary="Register a client account (no master profile)",
    description=(
        "Creates a user without a master profile for clients accepting an invitation. "
        "Sends the same email verification flow as master registration."
    ),
    response_model=RegisterAcceptedOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {
            "model": ErrorDetail,
            "description": "This email is already registered.",
        },
    },
)
async def register_client(
    payload: RegisterClientPayload,
    use_case: Annotated[RegisterClientAccountUseCase, Depends(get_register_client_account_use_case)],
) -> RegisterAcceptedOut:
    return await use_case(payload)


@router.post(
    path="/verify-email",
    summary="Verify email with token from link",
    description=(
        "Accepts the signed token from the verification email. The SPA usually reads `token` from "
        "`/verify-email?token=...` and submits it here. On valid token: sets `email_verified_at`, "
        "issues an httpOnly session cookie, and returns the user profile."
    ),
    response_model=UserSchema,
    response_description="Email verified; session cookie issued; user may access protected routes.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorDetail,
            "description": "Invalid, expired, or tampered verification token, or email no longer matches the token.",
        },
    },
)
async def verify_email(
    request: Request,
    payload: VerifyEmailPayload,
    response: Response,
    use_case: Annotated[VerifyEmailUseCase, Depends(get_verify_email_use_case)],
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
) -> UserSchema:
    settings = request.app.state.settings
    user = await use_case(secret=settings.security.secret_key, token=payload.token)
    await session_manager.attach_session(response, user.id)
    return user


@router.post(
    path="/login",
    summary="Sign in with email and password",
    description=(
        "Validates credentials for an existing user whose email is already verified. On success: issues an httpOnly "
        "session cookie (same as after `/auth/verify-email`). Use `/auth/me` to read the profile."
    ),
    response_model=UserSchema,
    response_description="Authenticated; session cookie set.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorDetail,
            "description": "Unknown email or wrong password.",
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorDetail,
            "description": "Email not verified yet, or account is disabled.",
        },
    },
)
async def login(
    response: Response,
    payload: LoginPayload,
    use_case: Annotated[LoginUseCase, Depends(get_login_use_case)],
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
) -> UserSchema:
    user = await use_case(email=payload.email, password=payload.password)
    await session_manager.attach_session(response, user.id)
    return user


@router.get(
    path="/me",
    summary="Current authenticated user",
    description=(
        "Returns the user profile for the active session (httpOnly cookie). Requires a prior successful "
        "`/auth/login` or `/auth/verify-email`. Responds with 401 if there is no valid session, and 403 if the "
        "user’s email is not verified."
    ),
    response_model=UserMeOut,
    response_description="Profile for the session user.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorDetail,
            "description": "Missing or invalid session cookie.",
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorDetail,
            "description": "Session present but email is not verified.",
        },
    },
)
async def me(
    current: Annotated[User, Depends(require_user)],
    use_case: Annotated[MeUseCase, Depends(get_me_use_case)],
) -> UserMeOut:
    return await use_case(user=current)


@router.post(
    path="/logout",
    summary="Sign out and clear session",
    description=(
        "Deletes the server-side session and clears the httpOnly session cookie. Idempotent: succeeds even if "
        "there was no session."
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Session removed; empty body.",
)
async def logout(
    request: Request,
    response: Response,
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
) -> Response:
    await session_manager.clear_session(request, response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post(
    path="/forgot-password",
    summary="Request a password reset email",
    description=(
        "Sends a password reset link to the given email if the account exists and is verified. "
        "Always responds 204 to prevent email enumeration."
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="If the email exists, a reset link has been sent.",
)
async def forgot_password(
    payload: ForgotPasswordPayload,
    use_case: Annotated[ForgotPasswordUseCase, Depends(get_forgot_password_use_case)],
) -> Response:
    await use_case(email=str(payload.email))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    path="/reset-password",
    summary="Set a new password using a reset token",
    description=(
        "Accepts the signed token from the reset email and a new password. "
        "On success the password is updated; user must then log in normally."
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Password updated successfully.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorDetail,
            "description": "Invalid, expired, or tampered reset token.",
        },
    },
)
async def reset_password(
    request: Request,
    payload: ResetPasswordPayload,
    use_case: Annotated[ResetPasswordUseCase, Depends(get_reset_password_use_case)],
) -> Response:
    settings = request.app.state.settings
    await use_case(
        secret=settings.security.secret_key,
        token=payload.token,
        new_password=payload.new_password,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    path="/change-password",
    summary="Change password for the current user",
    description=(
        "Requires the current password for verification. "
        "On success the password is updated; existing session remains valid."
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Password changed successfully.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorDetail,
            "description": "Current password is incorrect.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorDetail,
            "description": "Not authenticated.",
        },
    },
)
async def change_password(
    payload: ChangePasswordPayload,
    current: Annotated[User, Depends(require_user)],
    use_case: Annotated[ChangePasswordUseCase, Depends(get_change_password_use_case)],
) -> Response:
    await use_case(
        user=current,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
