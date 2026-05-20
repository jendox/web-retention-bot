from __future__ import annotations

import httpx


class TelegramApi:
    def __init__(self, token: str) -> None:
        self._base = f"https://api.telegram.org/bot{token}"

    async def get_updates(self, *, offset: int | None, timeout: int = 25) -> list[dict]:
        params: dict[str, int] = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        async with httpx.AsyncClient(timeout=timeout + 10) as client:
            resp = await client.get(f"{self._base}/getUpdates", params=params)
            resp.raise_for_status()
            data = resp.json()
        if not data.get("ok"):
            return []
        return list(data.get("result") or [])

    async def send_message(self, *, chat_id: str, text: str) -> None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self._base}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )
            resp.raise_for_status()
            data = resp.json()
        if not data.get("ok"):
            msg = f"Telegram sendMessage failed: {data}"
            raise RuntimeError(msg)
