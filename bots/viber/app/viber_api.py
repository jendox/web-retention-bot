from __future__ import annotations

import httpx


class ViberApi:
    def __init__(self, auth_token: str) -> None:
        self._token = auth_token

    async def send_message(self, payload: dict) -> None:
        headers = {"X-Viber-Auth-Token": self._token}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://chatapi.viber.com/pa/send_message",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        if data.get("status") != 0:
            msg = f"Viber send_message failed: {data}"
            raise RuntimeError(msg)
