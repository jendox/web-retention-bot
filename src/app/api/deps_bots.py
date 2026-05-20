from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from app.core.config import Settings, get_settings


def verify_bot_internal_secret(
    request: Request,
    x_bot_secret: Annotated[str | None, Header(alias="X-Bot-Secret")] = None,
) -> None:
    settings: Settings = request.app.state.settings
    expected = settings.messenger_bots.internal_secret
    if not expected or x_bot_secret != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid bot secret.")


def get_messenger_bot_clients(request: Request):
    from app.services.messenger.bot_clients import MessengerBotClients

    return MessengerBotClients(request.app.state.settings.messenger_bots)
