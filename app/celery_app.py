"""Celery entrypoint for the production profile.

The core local path does not import Celery.  Installing
``requirements-production.txt`` and starting the Compose ``core`` profile
enables the worker without changing the synchronous learning API.
"""

from __future__ import annotations

from app.config import get_settings

try:
    from celery import Celery
except ModuleNotFoundError:  # pragma: no cover - exercised only without optional profile
    Celery = None  # type: ignore[assignment,misc]


settings = get_settings()

if Celery is not None:
    celery_app = Celery(
        settings.celery_app_name,
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["app.tasks"],
    )
    celery_app.conf.update(
        task_track_started=True,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )
else:
    celery_app = None
