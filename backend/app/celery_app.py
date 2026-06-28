"""Celery application configuration.

Configures Celery to use Redis as broker and result backend,
with task autodiscovery for the app.tasks package.
"""

from celery import Celery

from app.config import settings

# Create Celery instance
celery_app = Celery(
    "ai_image_gen",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Configure Celery
celery_app.conf.update(
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Result expiration (1 hour)
    result_expires=3600,
    # Track task state when started
    task_track_started=True,
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Concurrency settings
    worker_concurrency=4,
    worker_prefetch_multiplier=1,
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Autodiscover tasks in app.tasks package
celery_app.autodiscover_tasks(["app.tasks"])
