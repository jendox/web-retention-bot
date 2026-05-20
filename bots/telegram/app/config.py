from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BotConfig:
    telegram_bot_token: str
    bot_internal_secret: str
    retention_api_url: str
    telegram_mode: str
    listen_host: str
    listen_port: int
    webhook_path: str
    webhook_secret: str | None
    welcome_text: str

    @classmethod
    def from_env(cls) -> BotConfig:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            msg = "TELEGRAM_BOT_TOKEN is required"
            raise ValueError(msg)
        return cls(
            telegram_bot_token=token,
            bot_internal_secret=os.environ.get("BOT_INTERNAL_SECRET", "dev-bot-internal-secret-change-me").strip(),
            retention_api_url=os.environ.get("RETENTION_API_URL", "http://host.docker.internal:8000").strip(),
            telegram_mode=os.environ.get("TELEGRAM_MODE", "polling").strip().lower(),
            listen_host=os.environ.get("LISTEN_HOST", "0.0.0.0"),
            listen_port=int(os.environ.get("LISTEN_PORT", "8091")),
            webhook_path=os.environ.get("TELEGRAM_WEBHOOK_PATH", "/telegram/webhook"),
            webhook_secret=os.environ.get("TELEGRAM_WEBHOOK_SECRET") or None,
            welcome_text=os.environ.get(
                "TELEGRAM_WELCOME_TEXT",
                "Retention Studio: нажмите Start по ссылке из настроек, чтобы получать уведомления.",
            ),
        )
