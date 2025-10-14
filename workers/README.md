# Celery Workers

**AAET-87: Celery Integration**

Async background workers for repository parsing and ingestion.

## Overview

This package contains Celery tasks for:
- Repository parsing and code graph construction
- Background job processing with retry logic
- Progress tracking and monitoring
- Multi-tenant isolation

## Architecture

```
┌─────────────┐      ┌──────────┐      ┌─────────────┐
│   FastAPI   │─────▶│  Redis   │─────▶│   Celery    │
│   (API)     │      │ (Broker) │      │   Worker    │
└─────────────┘      └──────────┘      └─────────────┘
                                              │
                                              ▼
                                        ┌──────────────┐
                                        │  PostgreSQL  │
                                        │  (Storage)   │
                                        └──────────────┘
```

## Setup

### 1. Install Dependencies

```bash
pip install celery redis
```

### 2. Configure Environment

```bash
# .env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

### 3. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or using docker-compose
docker-compose up -d redis
```

### 4. Start Celery Worker

```bash
# From project root
celery -A workers.celery_app worker --loglevel=info

# With concurrency
celery -A workers.celery_app worker --loglevel=info --concurrency=4

# With autoscaling
celery -A workers.celery_app worker --loglevel=info --autoscale=10,3
```

### 5. Start Flower (Optional Monitoring)

```bash
celery -A workers.celery_app flower --port=5555
```

Then visit http://localhost:5555

## Usage

### Trigger Task from Code

```python
from workers.tasks import parse_and_index_repository

# Async execution (returns immediately)
task = parse_and_index_repository.delay(
    tenant_id="tenant-123",
    repo_id="repo-456",
    repo_path="/path/to/repository",
    connection_string="postgresql://user:pass@localhost/dbname"
)

# Get task ID
print(f"Task ID: {task.id}")

# Check status
print(f"Status: {task.state}")  # PENDING, STARTED, SUCCESS, FAILURE

# Get result (blocks until complete)
result = task.get(timeout=3600)
print(f"Success: {result['success']}")
print(f"Nodes: {result['nodes_created']}")
print(f"Edges: {result['edges_created']}")
```

### Check Task Progress

```python
from celery.result import AsyncResult

# Get task by ID
task = AsyncResult(task_id, app=celery_app)

# Check state
print(task.state)  # PENDING, STARTED, PROGRESS, SUCCESS, FAILURE

# Get progress info
if task.state == 'PROGRESS':
    info = task.info
    print(f"Status: {info['status']}")
    print(f"Progress: {info['progress']}%")
    print(f"Nodes: {info.get('nodes_created', 0)}")
```

### Trigger Task from API

```python
from fastapi import APIRouter
from workers.tasks import parse_and_index_repository

router = APIRouter()

@router.post("/repositories/parse")
async def trigger_parse(
    tenant_id: str,
    repo_id: str,
    repo_path: str
):
    # Trigger async task
    task = parse_and_index_repository.delay(
        tenant_id=tenant_id,
        repo_id=repo_id,
        repo_path=repo_path,
        connection_string=settings.DATABASE_URL
    )
    
    return {
        "task_id": task.id,
        "status": "queued"
    }

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    task = AsyncResult(task_id, app=celery_app)
    
    if task.state == 'PENDING':
        return {"status": "pending"}
    elif task.state == 'STARTED':
        return {"status": "started"}
    elif task.state == 'PROGRESS':
        return {
            "status": "in_progress",
            **task.info
        }
    elif task.state == 'SUCCESS':
        return {
            "status": "success",
            **task.result
        }
    elif task.state == 'FAILURE':
        return {
            "status": "failed",
            "error": str(task.info)
        }
```

## Task Configuration

### Retry Logic

Tasks automatically retry on transient errors:
- **Max retries:** 3
- **Base delay:** 60 seconds
- **Backoff:** Exponential (60s, 120s, 240s)
- **Max delay:** 600 seconds (10 minutes)
- **Jitter:** Enabled (prevents thundering herd)

**Auto-retry errors:**
- `StorageError` - Database connection issues
- `ConnectionError` - Network issues

**No-retry errors:**
- `TenantValidationError` - Invalid input
- `RepositoryParseError` - Bad repository structure

### Time Limits

- **Soft limit:** 55 minutes (raises `SoftTimeLimitExceeded`)
- **Hard limit:** 60 minutes (kills task)

### Progress Tracking

Tasks report progress at key stages:
1. **0%** - Task queued
2. **10%** - Connecting to database
3. **20%** - Creating parser service
4. **30%** - Parsing repository
5. **100%** - Complete

## Monitoring

### Celery Events

```bash
# Monitor events in real-time
celery -A workers.celery_app events
```

### Task Stats

```bash
# Get worker stats
celery -A workers.celery_app inspect stats

# Get active tasks
celery -A workers.celery_app inspect active

# Get scheduled tasks
celery -A workers.celery_app inspect scheduled
```

### Flower Dashboard

Access at http://localhost:5555 to see:
- Active workers
- Task history
- Success/failure rates
- Task duration graphs
- Worker resource usage

## Production Deployment

### Systemd Service

```ini
# /etc/systemd/system/celery-worker.service
[Unit]
Description=Celery Worker
After=network.target

[Service]
Type=forking
User=celery
Group=celery
WorkingDirectory=/app
Environment="CELERY_BROKER_URL=redis://redis:6379/0"
ExecStart=/usr/local/bin/celery -A workers.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=1000

[Install]
WantedBy=multi-user.target
```

### Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN pip install -e .

CMD ["celery", "-A", "workers.celery_app", "worker", "--loglevel=info"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: worker
        image: aelus-aether:latest
        command: ["celery", "-A", "workers.celery_app", "worker"]
        env:
        - name: CELERY_BROKER_URL
          value: "redis://redis:6379/0"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

## Troubleshooting

### Task Stuck in PENDING

- Check if worker is running: `celery -A workers.celery_app inspect active`
- Check Redis connection: `redis-cli ping`
- Check worker logs for errors

### Task Failed with Retry

- Check task logs for error details
- Verify database connectivity
- Check if repository path exists

### High Memory Usage

- Reduce `worker_prefetch_multiplier` (default: 1)
- Lower `max_tasks_per_child` (default: 1000)
- Increase worker count, decrease concurrency per worker

## Next Steps

- **AAET-88:** Integration testing
- **AAET-89:** Documentation
- **AAET-91:** Storage enhancements

---

**Status:** ✅ AAET-87 Implementation Complete
