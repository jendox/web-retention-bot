from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

__all__ = ["celery_app", "create_celery_app"]


def create_celery_app() -> Celery:
    settings = get_settings()
    app = Celery(
        "web_retention_bot",
        broker=settings.celery.broker_url,
        backend=settings.celery.result_backend,
        # task_always_eager=settings.celery.task_always_eager,
        # task_eager_propagates=settings.celery.task_eager_propagates,
    )
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        broker_connection_retry_on_startup=True,
    )
    app.autodiscover_tasks(["app.services.notifications"], related_name="tasks", force=True)
    return app


celery_app = create_celery_app()
