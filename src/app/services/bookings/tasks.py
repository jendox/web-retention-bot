from __future__ import annotations

from celery import shared_task

from app.core.structured_logging import get_logger, log_context
from app.core.worker_async import run_worker_async
from app.core.worker_db import worker_db_session
from app.repositories.bookings import BookingRepository

logger = get_logger("app.booking.tasks")


async def _complete_past_scheduled_async() -> int:
    async with worker_db_session() as session:
        repo = BookingRepository(session)
        return await repo.complete_past_scheduled()


@shared_task(name="bookings.complete_past_scheduled")
def complete_past_scheduled() -> int:
    """Mark past SCHEDULED bookings as COMPLETED (runs on Celery Beat)."""
    with log_context(task="complete_past_scheduled"):
        try:
            updated = run_worker_async(_complete_past_scheduled_async())
        except Exception:
            logger.exception("failed")
            raise
        logger.info("completed", updated_count=updated)
        return updated
