import uuid

from starlette.testclient import TestClient

from app.main import app

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"


def _issue_csrf(client: TestClient) -> dict[str, str]:
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200, response.text
    token = client.cookies.get(CSRF_COOKIE)
    assert token
    return {CSRF_HEADER: token}


def test_login_rate_limit_uses_json_body_without_breaking_route_parsing():
    suffix = uuid.uuid4().hex[:8]
    email = f"missing_{suffix}@example.com"

    with TestClient(app) as client:
        headers = _issue_csrf(client)
        headers["X-Forwarded-For"] = f"10.10.{int(suffix[:2], 16)}.{int(suffix[2:4], 16)}"

        for _ in range(5):
            response = client.post(
                "/api/auth/login",
                json={"email": email, "password": "wrong-password"},
                headers=headers,
            )
            assert response.status_code == 401, response.text

        limited = client.post(
            "/api/auth/login",
            json={"email": email, "password": "wrong-password"},
            headers=headers,
        )
        assert limited.status_code == 429, limited.text
        assert limited.json()["detail"] == "Too many requests"
        assert limited.headers["Retry-After"]
        assert limited.headers["X-RateLimit-Limit"] == "5"
        assert limited.headers["X-RateLimit-Remaining"] == "0"
        assert limited.headers["X-RateLimit-Reset"]
        assert limited.headers["X-Request-Id"]


def test_login_rate_limit_key_is_scoped_by_email():
    suffix = uuid.uuid4().hex[:8]
    first_email = f"limited_{suffix}@example.com"
    second_email = f"other_{suffix}@example.com"

    with TestClient(app) as client:
        headers = _issue_csrf(client)
        headers["X-Forwarded-For"] = f"10.20.{int(suffix[:2], 16)}.{int(suffix[2:4], 16)}"

        for _ in range(5):
            response = client.post(
                "/api/auth/login",
                json={"email": first_email, "password": "wrong-password"},
                headers=headers,
            )
            assert response.status_code == 401, response.text

        first_limited = client.post(
            "/api/auth/login",
            json={"email": first_email, "password": "wrong-password"},
            headers=headers,
        )
        assert first_limited.status_code == 429, first_limited.text

        second_email_response = client.post(
            "/api/auth/login",
            json={"email": second_email, "password": "wrong-password"},
            headers=headers,
        )
        assert second_email_response.status_code == 401, second_email_response.text


def test_invitation_accept_regex_policy_is_rate_limited_before_csrf():
    suffix = uuid.uuid4().hex[:8]
    headers = {"X-Forwarded-For": f"10.30.{int(suffix[:2], 16)}.{int(suffix[2:4], 16)}"}

    with TestClient(app) as client:
        for _ in range(20):
            response = client.post(
                f"/api/invitations/{suffix}/accept",
                json={"display_name": "Client"},
                headers=headers,
            )
            assert response.status_code == 403, response.text
            assert response.json()["detail"] == "CSRF token missing or invalid"

        limited = client.post(
            f"/api/invitations/{suffix}/accept",
            json={"display_name": "Client"},
            headers=headers,
        )
        assert limited.status_code == 429, limited.text
        assert limited.headers["X-RateLimit-Limit"] == "20"
