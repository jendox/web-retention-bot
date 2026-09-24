from __future__ import annotations

from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.config import Settings
from app.core.security import verify_password
from app.core.structured_logging import get_logger
from app.models.user import User

__all__ = ["AllowlistAdminAuthBackend"]

logger = get_logger("app.admin.auth")


class AllowlistAdminAuthBackend(AuthenticationBackend):
    def __init__(self, *, settings: Settings, engine: Engine) -> None:
        session_secret = settings.admin.session_secret or settings.security.secret_key
        super().__init__(
            secret_key=session_secret,
            session_cookie="admin_session",
            https_only=settings.session.cookie_secure,
            same_site="lax",
        )
        self._engine = engine
        self._allowed_emails = settings.admin.allowed_email_set

    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = str(form.get("username", "")).strip().lower()
        password = str(form.get("password", ""))

        if not email or not password or email not in self._allowed_emails:
            logger.info("admin_login_failed", reason="not_allowed_or_empty", email=email or None)
            return False

        with Session(self._engine) as session:
            user = session.scalar(select(User).where(User.email == email))
            if user is None or not verify_password(password, user.password_hash):
                logger.info("admin_login_failed", reason="invalid_credentials", email=email)
                return False
            if user.email_verified_at is None:
                logger.info("admin_login_failed", reason="email_not_verified", email=email)
                return False
            if not user.is_active:
                logger.info("admin_login_failed", reason="inactive_user", email=email)
                return False

            request.session["user_id"] = str(user.id)
            logger.info("admin_login_success", user_id=str(user.id), email=email)
            return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("user_id") is not None
