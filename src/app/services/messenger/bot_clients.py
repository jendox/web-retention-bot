from __future__ import annotations

import httpx

from app.core.config import MessengerBotsSettings
from app.services.messenger.providers import MessengerProvider


class MessengerBotSendError(Exception):
    def __init__(self, provider: MessengerProvider, status_code: int, detail: str) -> None:
        self.provider = provider
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{provider.value} send failed: {status_code} {detail}")


class MessengerBotClients:
    """HTTP clients to lightweight bot sidecar containers."""

    def __init__(self, settings: MessengerBotsSettings) -> None:
        self._settings = settings

    def _service_url(self, provider: MessengerProvider) -> str | None:
        if provider == MessengerProvider.TELEGRAM:
            return self._settings.telegram_service_url
        return None

    async def send_text(
        self,
        provider: MessengerProvider,
        *,
        external_id: str,
        text: str,
    ) -> None:
        base = self._service_url(provider)
        if not base:
            raise MessengerBotSendError(provider, 503, "Bot service URL is not configured.")
        headers = {"X-Bot-Secret": self._settings.internal_secret, "Content-Type": "application/json"}
        payload = {"external_id": external_id, "text": text}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{base.rstrip('/')}/v1/send", json=payload, headers=headers)
        if resp.status_code >= 400:
            detail = resp.text
            try:
                detail = str(resp.json().get("detail", detail))
            except Exception:
                pass
            raise MessengerBotSendError(provider, resp.status_code, detail)
