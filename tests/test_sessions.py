import uuid

from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings
from app.services.sessions import SESSION_PREFIX, SessionManager, SessionStore


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str | bytes] = {}
        self.expirations: dict[str, int] = {}

    async def set(self, key, value, *, ex):
        self.values[key] = value
        self.expirations[key] = ex

    async def get(self, key):
        return self.values.get(key)

    async def delete(self, key):
        self.values.pop(key, None)


def _request_with_cookies(cookies: dict[str, str]) -> Request:
    headers = [(b"cookie", "; ".join(f"{key}={value}" for key, value in cookies.items()).encode())]
    return Request({"type": "http", "method": "POST", "path": "/", "headers": headers})


async def test_session_store_creates_looks_up_and_destroys_session():
    redis = FakeRedis()
    store = SessionStore(redis)
    user_id = uuid.uuid4()

    token = await store.create(user_id, ttl_seconds=123)

    assert token
    assert redis.values[f"{SESSION_PREFIX}{token}"] == str(user_id)
    assert redis.expirations[f"{SESSION_PREFIX}{token}"] == 123
    assert await store.lookup_user(token) == user_id

    await store.destroy(token)

    assert await store.lookup_user(token) is None


async def test_session_store_accepts_byte_user_id_from_redis():
    redis = FakeRedis()
    store = SessionStore(redis)
    user_id = uuid.uuid4()
    token = "token"
    redis.values[f"{SESSION_PREFIX}{token}"] = str(user_id).encode()

    assert await store.lookup_user(token) == user_id


async def test_session_manager_attaches_session_and_rotates_csrf_cookie():
    redis = FakeRedis()
    settings = Settings()
    manager = SessionManager(SessionStore(redis), settings)
    response = Response()
    user_id = uuid.uuid4()

    await manager.attach_session(response, user_id)

    set_cookie = response.headers.getlist("set-cookie")
    assert any(f"{settings.session.cookie_name}=" in value and "HttpOnly" in value for value in set_cookie)
    assert any(f"{settings.session.csrf_cookie_name}=" in value and "HttpOnly" not in value for value in set_cookie)
    assert len(redis.values) == 1
    assert next(iter(redis.values.values())) == str(user_id)


async def test_session_manager_clear_session_destroys_store_entry_and_clears_cookies():
    redis = FakeRedis()
    settings = Settings()
    manager = SessionManager(SessionStore(redis), settings)
    token = "session-token"
    redis.values[f"{SESSION_PREFIX}{token}"] = str(uuid.uuid4())
    request = _request_with_cookies({settings.session.cookie_name: token})
    response = Response()

    await manager.clear_session(request, response)

    assert redis.values == {}
    set_cookie = response.headers.getlist("set-cookie")
    assert any(value.startswith(f"{settings.session.cookie_name}=") and "Max-Age=0" in value for value in set_cookie)
    csrf_cleared = any(
        value.startswith(f"{settings.session.csrf_cookie_name}=") and "Max-Age=0" in value
        for value in set_cookie
    )
    assert csrf_cleared
