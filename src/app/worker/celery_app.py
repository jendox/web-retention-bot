from __future__ import annotations

from datetime import timedelta

from celery import Celery
from celery.signals import beat_init, worker_process_init

from app.core.config import get_settings
from app.core.structured_logging import configure_structlog, get_logger

__all__ = ["celery_app", "create_celery_app"]

logger = get_logger("app.celery")


def _configure_celery_logging() -> None:
    settings = get_settings()
    configure_structlog(
        debug=settings.app_env.lower() in {"dev", "development", "local", "test"},
        json_logs=settings.app_env.lower() not in {"dev", "development", "local", "test"},
    )


@worker_process_init.connect
def _on_worker_process_init(**_kwargs: object) -> None:
    _configure_celery_logging()
    logger.info("celery worker process ready")


@beat_init.connect
def _on_beat_init(**_kwargs: object) -> None:
    _configure_celery_logging()
    settings = get_settings()
    logger.info(
        "celery beat ready",
        complete_past_interval_minutes=settings.booking.complete_past_interval_minutes,
        note="Beat only enqueues tasks; run `make celery-worker` in another terminal.",
    )


def create_celery_app() -> Celery:
    settings = get_settings()
    app = Celery(
        "web_retention_bot",
        broker=settings.celery.broker_url,
        backend=settings.celery.result_backend,
    )
    interval_minutes = settings.booking.complete_past_interval_minutes
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        broker_connection_retry_on_startup=True,
        task_always_eager=settings.celery.task_always_eager,
        task_eager_propagates=settings.celery.task_eager_propagates,
        beat_schedule={
            "bookings-complete-past-scheduled": {
                "task": "bookings.complete_past_scheduled",
                "schedule": timedelta(minutes=interval_minutes),
            },
            "notifications-process-due-booking-reminders": {
                "task": "notifications.process_due_booking_reminders",
                "schedule": timedelta(seconds=settings.notifications.reminder_scan_interval_seconds),
            },
        },
    )
    app.autodiscover_tasks(
        ["app.services.notifications", "app.services.bookings"],
        related_name="tasks",
        force=True,
    )
    return app


celery_app = create_celery_app()
