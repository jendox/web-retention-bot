from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from uuid import UUID

_TOKEN_VERSION = 1


class EmailVerificationTokenError(ValueError):
    pass


def _pad_b64(data: str) -> str:
    return data + "=" * (-len(data) % 4)


def mint_email_verification_token(
    *,
    secret: str,
    user_id: UUID,
    email: str,
    ttl_seconds: int,
) -> str:
    expires_at = int(time.time()) + int(ttl_seconds)
    payload = {"v": _TOKEN_VERSION, "uid": str(user_id), "email": email.lower(), "exp": expires_at}
    body = (
        base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    )
    sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def parse_email_verification_token(*, secret: str, token: str) -> tuple[UUID, str]:
    try:
        body, sig_hex = token.rsplit(".", 1)
        expect = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        if len(sig_hex) != len(expect) or not hmac.compare_digest(sig_hex, expect):
            raise EmailVerificationTokenError("invalid_signature")
        raw = json.loads(base64.urlsafe_b64decode(_pad_b64(body)).decode())
        if raw.get("v") != _TOKEN_VERSION:
            raise EmailVerificationTokenError("unsupported_version")
        uid = UUID(raw["uid"])
        email = str(raw["email"]).lower()
        expires_at = int(raw["exp"])
    except EmailVerificationTokenError:
        raise
    except Exception as exc:
        raise EmailVerificationTokenError("malformed") from exc
    if int(time.time()) > expires_at:
        raise EmailVerificationTokenError("expired")
    return uid, email
