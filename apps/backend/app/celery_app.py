"""Celery app (optional worker for long jobs). Broker: Redis when REDIS_URL is set."""

from __future__ import annotations

import os

from celery import Celery

from app.settings import get_settings

settings = get_settings()
broker = settings.redis_url or os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")

celery_app = Celery("teambition_backend", broker=broker, backend=broker)


@celery_app.task(name="teambition.ping")
def ping() -> str:
    return "pong"
