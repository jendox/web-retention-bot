from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import SessionStore, get_session_store, require_user
from app.core.config import Settings, get_settings
from app.core.verification_token import EmailVerificationTokenError
from app.models.user import User
from app.schemas.auth import (
    LoginPayload,
    RegisterAcceptedOut,
    RegisterClientPayload,
    RegisterPayload,
    VerifyEmailPayload,
)
from app.schemas.errors import ErrorDetail
from app.schemas.user import UserSchema
from app.services.notifications.dispatcher import (
    NotificationDispatcher,
    get_notification_dispatcher,
)
from app.use_cases.login import (
    EmailNotVerifiedError,
    InactiveUserError,
    InvalidCredentialsError,
    LoginUseCase,
    get_login_use_case,
)
from app.use_cases.register_master import RegisterMasterUseCase, get_register_master_use_case
from app.use_cases.register_user import RegisterUserUseCase, UserAlreadyExists, get_register_user_use_case
from app.use_cases.verify_email import VerifyEmailUseCase, get_verify_email_use_case

router = APIRouter(prefix="/auth", tags=["auth"])


async def _attach_session(settings: Settings, response: Response, store: SessionStore, user_id: UUID) -> None:
    token = await store.create(user_id, settings.session.ttl_seconds)
    response.set_cookie(
        key=settings.session.cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.session.cookie_secure,
        max_age=settings.session.ttl_seconds,
        path="/",
    )


async def _clear_session(response: Response, store: SessionStore, cookie_value: str | None) -> None:
    await store.destroy(cookie_value)
    settings = get_settings()
    response.delete_cookie(settings.session.cookie_name, path="/")


@router.post(
    path="/register",
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
async def register(
    payload: RegisterPayload,
    register_user_use_case: Annotated[RegisterUserUseCase, Depends(get_register_user_use_case)],
    register_master_use_case: Annotated[RegisterMasterUseCase, Depends(get_register_master_use_case)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> RegisterAcceptedOut:
    try:
        user = await register_user_use_case(payload)
        await register_master_use_case(user, display_name=payload.master_display_name)
        await dispatcher.dispatch_email_verification(user_id=user.id, to_email=user.email)

        return RegisterAcceptedOut(id=user.id, email=user.email)
    except UserAlreadyExists:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="User already exists.") from None


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
    register_user_use_case: Annotated[RegisterUserUseCase, Depends(get_register_user_use_case)],
    dispatcher: Annotated[NotificationDispatcher, Depends(get_notification_dispatcher)],
) -> RegisterAcceptedOut:
    try:
        user = await register_user_use_case.register_client(
            email=str(payload.email),
            password=payload.password,
        )
        await dispatcher.dispatch_email_verification(user_id=user.id, to_email=user.email)
        return RegisterAcceptedOut(id=user.id, email=user.email)
    except UserAlreadyExists:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="User already exists.") from None


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
    verify_email_use_case: Annotated[VerifyEmailUseCase, Depends(get_verify_email_use_case)],
    store: Annotated[SessionStore, Depends(get_session_store)],
) -> UserSchema:
    settings = request.app.state.settings
    try:
        user = await verify_email_use_case(secret=settings.security.secret_key, token=payload.token)
        await _attach_session(settings, response, store, user.id)
        return user
    except EmailVerificationTokenError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link",
        ) from None


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
    request: Request,
    response: Response,
    payload: LoginPayload,
    login_use_case: Annotated[LoginUseCase, Depends(get_login_use_case)],
    store: Annotated[SessionStore, Depends(get_session_store)],
) -> UserSchema:
    settings = request.app.state.settings
    try:
        user = await login_use_case(email=payload.email, password=payload.password)
    except InvalidCredentialsError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from None
    except EmailNotVerifiedError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Email address is not verified yet",
        ) from None
    except InactiveUserError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        ) from None
    await _attach_session(settings, response, store, user.id)
    return user


@router.get(
    path="/me",
    summary="Current authenticated user",
    description=(
        "Returns the user profile for the active session (httpOnly cookie). Requires a prior successful "
        "`/auth/login` or `/auth/verify-email`. Responds with 401 if there is no valid session, and 403 if the "
        "user’s email is not verified."
    ),
    response_model=UserSchema,
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
async def me(current: Annotated[User, Depends(require_user)]) -> UserSchema:
    return UserSchema.from_model(current)


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
    store: Annotated[SessionStore, Depends(get_session_store)],
) -> Response:
    settings = request.app.state.settings
    token = request.cookies.get(settings.session.cookie_name)
    await _clear_session(response, store, token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
