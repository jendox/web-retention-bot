from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from retention_shared.api import RetentionApi
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from app.config import BotConfig
from app.handlers import handle_update
from app.telegram_api import TelegramApi

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("telegram_bot")


def _verify_secret(request: Request, expected: str) -> bool:
    return request.headers.get("X-Bot-Secret") == expected


async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "telegram-bot"})


async def send_message(request: Request) -> Response:
    config: BotConfig = request.app.state.config
    if not _verify_secret(request, config.bot_internal_secret):
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    body = await request.json()
    chat_id = str(body.get("external_id", "")).strip()
    text = str(body.get("text", "")).strip()
    if not chat_id or not text:
        return JSONResponse({"detail": "external_id and text are required"}, status_code=400)

    telegram: TelegramApi = request.app.state.telegram
    await telegram.send_message(chat_id=chat_id, text=text)
    return JSONResponse({"status": "sent"})


async def telegram_webhook(request: Request) -> Response:
    config: BotConfig = request.app.state.config
    if config.webhook_secret:
        header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header != config.webhook_secret:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    update = await request.json()
    await handle_update(
        config,
        request.app.state.telegram,
        request.app.state.retention,
        update,
    )
    return JSONResponse({"ok": True})


async def _polling_loop(app: Starlette) -> None:
    config: BotConfig = app.state.config
    telegram: TelegramApi = app.state.telegram
    retention: RetentionApi = app.state.retention
    offset: int | None = None
    logger.info("telegram_polling_started")
    while True:
        try:
            updates = await telegram.get_updates(offset=offset)
            for update in updates:
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    offset = update_id + 1
                await handle_update(config, telegram, retention, update)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("polling_error")
            await asyncio.sleep(3)


@asynccontextmanager
async def lifespan(app: Starlette):
    config = BotConfig.from_env()
    app.state.config = config
    app.state.telegram = TelegramApi(config.telegram_bot_token)
    app.state.retention = RetentionApi(
        base_url=config.retention_api_url,
        internal_secret=config.bot_internal_secret,
    )

    poll_task: asyncio.Task | None = None
    if config.telegram_mode == "polling":
        poll_task = asyncio.create_task(_polling_loop(app))

    yield

    if poll_task is not None:
        poll_task.cancel()
        try:
            await poll_task
        except asyncio.CancelledError:
            pass


app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Route("/v1/send", send_message, methods=["POST"]),
        Route("/telegram/webhook", telegram_webhook, methods=["POST"]),
    ],
    lifespan=lifespan,
)
