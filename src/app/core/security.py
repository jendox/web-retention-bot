from __future__ import annotations

from urllib.parse import quote
from uuid import UUID

from pwdlib import PasswordHash

from app.core.password_reset_token import mint_password_reset_token
from app.core.verification_token import mint_email_verification_token

__all__ = [
    "hash_password",
    "pwd_hasher",
    "verify_password",
    "generate_email_verification_url",
    "generate_password_reset_url",
]

pwd_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return pwd_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_hasher.verify(password, hashed)
    except ValueError:
        return False


def generate_email_verification_url(
    *,
    secret_key: str,
    user_id: UUID,
    email: str,
    base_url: str,
    verification_ttl_seconds: int,
) -> str:
    raw_token = mint_email_verification_token(
        secret=secret_key,
        user_id=user_id,
        email=email,
        ttl_seconds=verification_ttl_seconds,
    )
    safe_path = quote(raw_token, safe="")
    return f"{base_url.rstrip('/')}/verify-email?token={safe_path}"


def generate_password_reset_url(
    *,
    secret_key: str,
    user_id: UUID,
    email: str,
    base_url: str,
    password_reset_ttl_seconds: int,
) -> str:
    raw_token = mint_password_reset_token(
        secret=secret_key,
        user_id=user_id,
        email=email,
        ttl_seconds=password_reset_ttl_seconds,
    )
    safe_path = quote(raw_token, safe="")
    return f"{base_url.rstrip('/')}/reset-password?token={safe_path}"
