"""Minimal HTTP client for bot containers → Retention API (no app imports)."""

from __future__ import annotations

import httpx


class RetentionApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")


class RetentionApi:
    def __init__(self, *, base_url: str, internal_secret: str, timeout: float = 15.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._secret = internal_secret
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"X-Bot-Secret": self._secret, "Content-Type": "application/json"}

    async def complete_messenger_link(
        self,
        provider: str,
        *,
        token: str,
        external_id: str,
        display_name: str | None = None,
    ) -> dict:
        payload: dict[str, str] = {"token": token, "external_id": external_id}
        if display_name:
            payload["display_name"] = display_name
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/api/internal/messenger/{provider}/complete-link",
                json=payload,
                headers=self._headers(),
            )
        if resp.status_code >= 400:
            detail = resp.text
            try:
                body = resp.json()
                detail = body.get("detail", detail)
            except Exception:
                pass
            raise RetentionApiError(resp.status_code, str(detail))
        return resp.json()
