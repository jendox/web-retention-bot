from __future__ import annotations

import logging

from retention_api import RetentionApi, RetentionApiError

from app.config import BotConfig
from app.telegram_api import TelegramApi

logger = logging.getLogger("telegram_bot.handlers")


def _extract_start_token(text: str) -> str | None:
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        return None
    return parts[1].strip() or None


async def handle_update(config: BotConfig, telegram: TelegramApi, retention: RetentionApi, update: dict) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return

    text = (message.get("text") or "").strip()
    if not text.startswith("/start"):
        await telegram.send_message(
            chat_id=str(chat_id),
            text=config.welcome_text,
        )
        return

    token = _extract_start_token(text)
    if not token:
        await telegram.send_message(
            chat_id=str(chat_id),
            text="Откройте ссылку «Подключить Telegram» в настройках Retention Studio и нажмите Start.",
        )
        return

    display_name = chat.get("username")
    if display_name:
        display_name = f"@{display_name}"

    try:
        await retention.complete_messenger_link(
            "telegram",
            token=token,
            external_id=str(chat_id),
            display_name=display_name,
        )
    except RetentionApiError as exc:
        logger.warning("link_failed status=%s detail=%s", exc.status_code, exc.detail)
        await telegram.send_message(
            chat_id=str(chat_id),
            text="Ссылка недействительна или устарела. Запросите новую в настройках приложения.",
        )
        return

    await telegram.send_message(
        chat_id=str(chat_id),
        text="Telegram подключён. Уведомления Retention Studio будут приходить сюда.",
    )
