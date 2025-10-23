"""Celery application configuration.

AAET-87: Celery Integration
"""

import os
import sys
from celery import Celery

# Validate required environment variables at startup
REQUIRED_ENV_VARS = {
    "DATABASE_URL": "PostgreSQL connection string",
    "VOYAGE_API_KEY": "Voyage AI API key for embeddings",
    "CELERY_BROKER_URL": "Redis broker URL (optional, has default)",
    "CELERY_RESULT_BACKEND": "Redis result backend URL (optional, has default)",
}

missing_critical = []
for var, description in REQUIRED_ENV_VARS.items():
    if not os.getenv(var):
        # CELERY_BROKER_URL and CELERY_RESULT_BACKEND have defaults
        if var in ("CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"):
            continue
        missing_critical.append(f"  - {var}: {description}")

if missing_critical:
    print("❌ ERROR: Missing required environment variables:", file=sys.stderr)
    print("\n".join(missing_critical), file=sys.stderr)
    print("\nPlease set these variables before starting Celery workers.", file=sys.stderr)
    sys.exit(1)

# Create Celery app
celery_app = Celery(
    "aelus-aether",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)

# Configure Celery
# Note: Async tasks (async def) in Celery 5.5+ work by running asyncio.run() internally
# Celery wraps async tasks and executes them in an event loop automatically
# 
# Worker Pool Options for Async Tasks:
# - Development: celery -A workers.celery_app worker --pool=solo --loglevel=info
#   (solo pool runs tasks sequentially in main thread, good for debugging)
# 
# - Production:  celery -A workers.celery_app worker --pool=gevent --concurrency=100 --loglevel=info
#   (gevent pool provides high concurrency for I/O-bound async tasks)
# 
# - Alternative: celery -A workers.celery_app worker --pool=eventlet --concurrency=100 --loglevel=info
#   (eventlet is similar to gevent, choose based on your preference)
# 
# ⚠️ DO NOT use 'prefork' pool with async tasks - it's designed for CPU-bound sync tasks
# ⚠️ Install gevent: pip install gevent (or eventlet: pip install eventlet)
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
