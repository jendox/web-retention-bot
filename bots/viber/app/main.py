from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from retention_api import RetentionApi
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from app.config import ViberBotConfig
from app.handlers import handle_viber_event
from app.viber_api import ViberApi

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("viber_bot")


def _verify_secret(request: Request, expected: str) -> bool:
    return request.headers.get("X-Bot-Secret") == expected


async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "viber-bot"})


async def send_message(request: Request) -> Response:
    config: ViberBotConfig = request.app.state.config
    if not _verify_secret(request, config.bot_internal_secret):
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    if not config.viber_auth_token:
        return JSONResponse({"detail": "Viber bot is not configured"}, status_code=503)

    body = await request.json()
    receiver = str(body.get("external_id", "")).strip()
    text = str(body.get("text", "")).strip()
    if not receiver or not text:
        return JSONResponse({"detail": "external_id and text are required"}, status_code=400)

    viber: ViberApi = request.app.state.viber
    await viber.send_message(
        {
            "receiver": receiver,
            "type": "text",
            "text": text,
            "min_api_version": 7,
        },
    )
    return JSONResponse({"status": "sent"})


async def viber_webhook(request: Request) -> Response:
    config: ViberBotConfig = request.app.state.config
    event = await request.json()
    reply = await handle_viber_event(config, request.app.state.retention, event)
    if reply and config.viber_auth_token:
        viber: ViberApi = request.app.state.viber
        await viber.send_message(reply)
    return JSONResponse({"status": 0})


@asynccontextmanager
async def lifespan(app: Starlette):
    config = ViberBotConfig.from_env()
    app.state.config = config
    app.state.retention = RetentionApi(
        base_url=config.retention_api_url,
        internal_secret=config.bot_internal_secret,
    )
    app.state.viber = ViberApi(config.viber_auth_token) if config.viber_auth_token else None
    if not config.viber_auth_token:
        logger.warning("VIBER_AUTH_TOKEN not set — webhook will accept events but cannot send replies")
    yield


app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Route("/v1/send", send_message, methods=["POST"]),
        Route("/viber/webhook", viber_webhook, methods=["POST"]),
    ],
    lifespan=lifespan,
)
