import uuid

import pytest

from app.core.verification_token import (
    EmailVerificationTokenError,
    mint_email_verification_token,
    parse_email_verification_token,
)


def test_mint_parse_roundtrip():
    secret = "unit-test-secret"
    uid = uuid.uuid4()
    tok = mint_email_verification_token(
        secret=secret,
        user_id=uid,
        email="User@Example.com",
        ttl_seconds=3600,
    )
    got_id, got_email = parse_email_verification_token(secret=secret, token=tok)
    assert got_id == uid
    assert got_email == "user@example.com"


def test_parse_rejects_bad_sig():
    secret = "unit-test-secret"
    uid = uuid.uuid4()
    tok = mint_email_verification_token(
        secret=secret,
        user_id=uid,
        email="a@b.c",
        ttl_seconds=3600,
    )
    broken = tok[:-4] + "dead"
    with pytest.raises(EmailVerificationTokenError):
        parse_email_verification_token(secret=secret, token=broken)
