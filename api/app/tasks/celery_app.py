"""Celery application configuration."""
import os
from celery import Celery

# Use environment variable directly to avoid settings initialization issues
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "crm_dedup",
    broker=redis_url,
    backend=redis_url,
    include=["app.tasks.scan_tasks", "app.tasks.merge_tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,  # Process one task at a time
)
