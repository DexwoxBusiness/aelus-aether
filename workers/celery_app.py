"""Celery application configuration.

AAET-87: Celery Integration
"""

import os
from celery import Celery

# Create Celery app
celery_app = Celery(
    "aelus-aether",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)

# Configure Celery
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
    
    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["workers.tasks"])
