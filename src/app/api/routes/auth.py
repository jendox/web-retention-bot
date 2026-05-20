from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user
from app.core.database import get_db_session
from app.core.verification_token import EmailVerificationTokenError
from app.models.user import User
from app.repositories.clients import ClientRepository
from app.schemas.auth import (
    LoginPayload,
    RegisterAcceptedOut,
    RegisterClientPayload,
    RegisterPayload,
    VerifyEmailPayload,
)
from app.schemas.errors import ErrorDetail
from app.schemas.user import UserMeOut, UserSchema
from app.services.notifications.dispatcher import (
    NotificationDispatcher,
    get_notification_dispatcher,
)
from app.services.sessions import SessionManager, get_session_manager
from app.use_cases.auth import (
    EmailNotVerifiedError,
    InactiveUserError,
    InvalidCredentialsError,
    LoginUseCase,
    RegisterMasterUseCase,
    RegisterUserUseCase,
    UserAlreadyExists,
    VerifyEmailUseCase,
    get_login_use_case,
    get_register_master_use_case,
    get_register_user_use_case,
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
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
) -> UserSchema:
    settings = request.app.state.settings
    try:
        user = await verify_email_use_case(secret=settings.security.secret_key, token=payload.token)
        await session_manager.attach_session(response, user.id)
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
    response: Response,
    payload: LoginPayload,
    login_use_case: Annotated[LoginUseCase, Depends(get_login_use_case)],
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
) -> UserSchema:
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
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserMeOut:
    base = UserSchema.model_validate(current)
    client = await ClientRepository(session).primary_client_profile_for_user(current.id)
    return UserMeOut(
        **base.model_dump(),
        client_display_name=client.display_name if client else None,
        client_phone=client.phone if client else None,
    )


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
