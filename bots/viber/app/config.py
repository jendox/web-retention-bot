from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ViberBotConfig:
    viber_auth_token: str | None
    bot_internal_secret: str
    retention_api_url: str
    listen_port: int
    welcome_text: str

    @classmethod
    def from_env(cls) -> ViberBotConfig:
        token = os.environ.get("VIBER_AUTH_TOKEN", "").strip() or None
        return cls(
            viber_auth_token=token,
            bot_internal_secret=os.environ.get("BOT_INTERNAL_SECRET", "dev-bot-internal-secret-change-me").strip(),
            retention_api_url=os.environ.get("RETENTION_API_URL", "http://host.docker.internal:8000").strip(),
            listen_port=int(os.environ.get("LISTEN_PORT", "8092")),
            welcome_text=os.environ.get(
                "VIBER_WELCOME_TEXT",
                "Retention Studio: откройте ссылку из настроек приложения, чтобы подключить Viber.",
            ),
        )
