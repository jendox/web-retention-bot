from __future__ import annotations

import logging
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

import structlog
from structlog.contextvars import (
    bind_contextvars,
    clear_contextvars,
    get_contextvars,
    merge_contextvars,
    unbind_contextvars,
)

LOG_TIME_FORMAT = "iso"


def configure_structlog(*, debug: bool = False, json_logs: bool = True) -> None:
    """Configure stdlib logging and structlog once during application startup.

    The configuration keeps stdlib loggers usable while making structlog loggers
    emit the same structured shape. Context added via ``log_context`` or
    ``bind_request_context`` is stored in contextvars, so it is isolated per
    request/task and automatically available to every logger call in that scope.
    """

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if debug else logging.INFO,
        force=True,
    )

    shared_processors: list[structlog.types.Processor] = [
        merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt=LOG_TIME_FORMAT, utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer: structlog.types.Processor
    if json_logs:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


@contextmanager
def log_context(**values: Any) -> Iterator[None]:
    """Temporarily bind structured context values.

    Example:
        with log_context(use_case="accept_invitation", invitation_id=str(invite.id)):
            logger.info("started")

    Values are removed on exit, including when an exception is raised.
    """

    clean_values = {key: value for key, value in values.items() if value is not None}
    bind_contextvars(**clean_values)
    try:
        yield
    finally:
        if clean_values:
            unbind_contextvars(*clean_values.keys())


def bind_request_context(
    *,
    request_id: str,
    method: str,
    path: str,
    client_ip: str | None,
    user_agent: str | None,
    extra: Mapping[str, Any] | None = None,
) -> None:
    values: dict[str, Any] = {
        "request_id": request_id,
        "http_method": method,
        "path": path,
        "client_ip": client_ip,
        "user_agent": user_agent,
    }
    if extra:
        values.update(extra)
    bind_contextvars(**{key: value for key, value in values.items() if value is not None})


def clear_log_context() -> None:
    clear_contextvars()


def get_log_context() -> dict[str, Any]:
    return dict(get_contextvars())


def get_request_id() -> str | None:
    request_id = get_log_context().get("request_id")
    return str(request_id) if request_id is not None else None
