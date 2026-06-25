from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass

from app.core.database import Database

__all__ = ["reset_worker_async", "run_worker_async", "shutdown_worker_async"]


@dataclass
class _WorkerAsyncState:
    loop: asyncio.AbstractEventLoop | None = None


_STATE = _WorkerAsyncState()


def reset_worker_async() -> None:
    """Drop inherited async state after Celery forks a worker process."""
    _STATE.loop = None


def _worker_event_loop() -> asyncio.AbstractEventLoop:
    if _STATE.loop is None or _STATE.loop.is_closed():
        _STATE.loop = asyncio.new_event_loop()
    return _STATE.loop


def run_worker_async[T](awaitable: Awaitable[T]) -> T:
    loop = _worker_event_loop()
    if loop.is_running():
        raise RuntimeError("worker async loop is already running")
    return loop.run_until_complete(awaitable)


def shutdown_worker_async() -> None:
    loop = _STATE.loop
    if loop is None or loop.is_closed():
        if Database.engine is None:
            _STATE.loop = None
            return
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(Database._close())
        finally:
            loop.close()
        _STATE.loop = None
        return

    try:
        loop.run_until_complete(Database._close())
    finally:
        loop.close()
        _STATE.loop = None
