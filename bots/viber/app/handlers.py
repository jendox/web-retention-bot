from __future__ import annotations

import logging

from retention_shared.api import RetentionApi, RetentionApiError

from app.config import ViberBotConfig

logger = logging.getLogger("viber_bot.handlers")


async def handle_viber_event(config: ViberBotConfig, retention: RetentionApi, event: dict) -> dict | None:
    """Process Viber webhook JSON. Returns optional reply payload for send_message."""
    if not config.viber_auth_token:
        logger.warning("viber_token_missing")
        return None

    event_type = event.get("event")
    if event_type == "webhook":
        return {"status": 0, "status_message": "ok", "event_types": ["subscribed", "conversation_started", "message"]}

    if event_type in {"subscribed", "conversation_started"}:
        user = event.get("user") or event.get("sender") or {}
        context = (event.get("context") or "").strip()
        if not context:
            return _text_reply(user.get("id"), config.welcome_text)

        viber_id = user.get("id")
        if not viber_id:
            return None

        try:
            await retention.complete_messenger_link(
                "viber",
                token=context,
                external_id=str(viber_id),
                display_name=user.get("name"),
            )
        except RetentionApiError as exc:
            logger.warning("link_failed status=%s detail=%s", exc.status_code, exc.detail)
            return _text_reply(
                viber_id,
                "Ссылка недействительна или устарела. Запросите новую в настройках Retention Studio.",
            )
        return _text_reply(viber_id, "Viber подключён. Уведомления Retention Studio будут приходить сюда.")

    return None


def _text_reply(receiver_id: str | None, text: str) -> dict | None:
    if not receiver_id:
        return None
    return {
        "receiver": receiver_id,
        "type": "text",
        "text": text,
        "min_api_version": 7,
    }
