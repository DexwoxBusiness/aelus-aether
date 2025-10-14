# AAET-87: Integrate code-graph-rag with Celery Tasks - COMPLETE ✅

**Date:** October 14, 2025  
**Status:** ✅ Implementation Complete

---

## Summary

Successfully integrated ParserService with Celery for async background processing of repository parsing and ingestion.

---

## What Was Implemented

### 1. Celery Application Configuration
**File:** `workers/celery_app.py`

**Features:**
- ✅ Celery app with Redis broker
- ✅ JSON serialization
- ✅ Task tracking enabled
- ✅ Time limits (1 hour hard, 55 min soft)
- ✅ Late acknowledgment for reliability
- ✅ Auto-discovery of tasks

### 2. Ingestion Task
**File:** `workers/tasks/ingestion.py`

**Features:**
- ✅ `parse_and_index_repository` Celery task
- ✅ Wraps ParserService for async execution
- ✅ Retry logic with exponential backoff
- ✅ Progress tracking (0%, 10%, 20%, 30%, 100%)
- ✅ Proper error handling (validation, storage, unexpected)
- ✅ Structured logging with tenant context
- ✅ Async/sync bridge (asyncio event loop)
- ✅ Resource cleanup (storage connections)

**Retry Configuration:**
- Max retries: 3
- Base delay: 60 seconds
- Exponential backoff: 60s → 120s → 240s
- Max delay: 600 seconds (10 minutes)
- Jitter enabled
- Auto-retry on: `StorageError`, `ConnectionError`
- No retry on: `TenantValidationError`, `RepositoryParseError`

### 3. Progress Tracking
Tasks report progress at key stages:
1. **0%** - Task queued (PENDING)
2. **10%** - Connecting to database (PROGRESS)
3. **20%** - Creating parser service (PROGRESS)
4. **30%** - Parsing repository (PROGRESS)
5. **100%** - Complete (SUCCESS)

### 4. Documentation
**File:** `workers/README.md`

**Includes:**
- Setup instructions
- Usage examples
- Configuration guide
- Monitoring with Flower
- Production deployment (systemd, Docker, Kubernetes)
- Troubleshooting guide

### 5. Tests
**File:** `tests/workers/test_ingestion_tasks.py`

**Test Coverage:**
- ✅ Successful task execution
- ✅ Validation error handling (no retry)
- ✅ Parse error handling (no retry)
- ✅ Storage error handling (auto-retry)
- ✅ Unexpected error handling
- ✅ Resource cleanup verification

---

## Files Created

1. ✅ `workers/__init__.py` - Package marker
2. ✅ `workers/celery_app.py` - Celery configuration (40 lines)
3. ✅ `workers/tasks/__init__.py` - Tasks package
4. ✅ `workers/tasks/ingestion.py` - Main ingestion task (370 lines)
5. ✅ `workers/README.md` - Complete documentation (400 lines)
6. ✅ `tests/workers/__init__.py` - Test package
7. ✅ `tests/workers/test_ingestion_tasks.py` - Task tests (150 lines)
8. ✅ `AAET-87-COMPLETE.md` - This summary

**Total:** 8 files, ~960 lines

---

## Usage Examples

### 1. Start Celery Worker

```bash
# Basic
celery -A workers.celery_app worker --loglevel=info

# With concurrency
celery -A workers.celery_app worker --loglevel=info --concurrency=4

# With monitoring (Flower)
celery -A workers.celery_app flower --port=5555
```

### 2. Trigger Task from Python

```python
from workers.tasks import parse_and_index_repository

# Async execution
task = parse_and_index_repository.delay(
    tenant_id="tenant-123",
    repo_id="repo-456",
    repo_path="/path/to/repo",
    connection_string="postgresql://user:pass@localhost/dbname"
)

# Get task ID
print(f"Task ID: {task.id}")

# Check status
print(f"Status: {task.state}")

# Get result (blocks)
result = task.get(timeout=3600)
print(f"Nodes: {result['nodes_created']}")
print(f"Edges: {result['edges_created']}")
```

### 3. Check Progress

```python
from celery.result import AsyncResult
from workers.celery_app import celery_app

task = AsyncResult(task_id, app=celery_app)

if task.state == 'PROGRESS':
    info = task.info
    print(f"Status: {info['status']}")
    print(f"Progress: {info['progress']}%")
```

### 4. FastAPI Integration

```python
from fastapi import APIRouter
from workers.tasks import parse_and_index_repository

router = APIRouter()

@router.post("/repositories/parse")
async def trigger_parse(tenant_id: str, repo_id: str, repo_path: str):
    task = parse_and_index_repository.delay(
        tenant_id=tenant_id,
        repo_id=repo_id,
        repo_path=repo_path,
        connection_string=settings.DATABASE_URL
    )
    return {"task_id": task.id, "status": "queued"}

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    task = AsyncResult(task_id, app=celery_app)
    return {
        "status": task.state,
        "info": task.info if task.state == 'PROGRESS' else None,
        "result": task.result if task.state == 'SUCCESS' else None
    }
```

---

## Architecture

```
┌─────────────┐      ┌──────────┐      ┌─────────────┐
│   FastAPI   │─────▶│  Redis   │─────▶│   Celery    │
│   (API)     │      │ (Broker) │      │   Worker    │
│             │      │          │      │             │
│ POST /parse │      │  Queue   │      │ parse_and_  │
│             │      │          │      │ index_repo  │
└─────────────┘      └──────────┘      └─────────────┘
      │                                       │
      │                                       ▼
      │                                 ┌──────────────┐
      │                                 │ ParserService│
      │                                 │              │
      │                                 │ GraphUpdater │
      │                                 └──────────────┘
      │                                       │
      ▼                                       ▼
┌──────────────────────────────────────────────────────┐
│                   PostgreSQL                          │
│  (code_nodes, code_edges, tenant isolation)          │
└──────────────────────────────────────────────────────┘
```

---

## Error Handling

### 1. Validation Errors (No Retry)
```python
# Invalid tenant_id or repo_id
# Returns: {"success": False, "error": "Tenant validation failed: ..."}
```

### 2. Parse Errors (No Retry)
```python
# Invalid repository structure
# Returns: {"success": False, "error": "Repository parse failed: ..."}
```

### 3. Storage Errors (Auto-Retry)
```python
# Database connection issues
# Automatically retries with exponential backoff
# After 3 retries, raises StorageError
```

### 4. Time Limit Exceeded
```python
# Task runs > 55 minutes (soft limit)
# Returns: {"success": False, "error": "Task exceeded time limit"}
```

### 5. Unexpected Errors
```python
# Any other exception
# Returns: {"success": False, "error": "Unexpected error: ..."}
```

---

## Monitoring

### Celery Events
```bash
celery -A workers.celery_app events
```

### Worker Stats
```bash
celery -A workers.celery_app inspect stats
celery -A workers.celery_app inspect active
```

### Flower Dashboard
```bash
celery -A workers.celery_app flower --port=5555
# Visit http://localhost:5555
```

**Flower Features:**
- Real-time task monitoring
- Success/failure rates
- Task duration graphs
- Worker resource usage
- Task history

---

## Production Deployment

### Docker Compose
```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  celery-worker:
    build: .
    command: celery -A workers.celery_app worker --loglevel=info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql://user:pass@db/dbname
    depends_on:
      - redis
      - db
  
  flower:
    build: .
    command: celery -A workers.celery_app flower --port=5555
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis
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

---

## Testing

Run tests:
```bash
pytest tests/workers/test_ingestion_tasks.py -v
```

Expected output:
```
tests/workers/test_ingestion_tasks.py::TestParseAndIndexRepository::test_task_success PASSED
tests/workers/test_ingestion_tasks.py::TestParseAndIndexRepository::test_task_validation_error PASSED
tests/workers/test_ingestion_tasks.py::TestParseAndIndexRepository::test_task_parse_error PASSED
tests/workers/test_ingestion_tasks.py::TestParseAndIndexRepository::test_task_storage_error_retries PASSED
tests/workers/test_ingestion_tasks.py::TestParseAndIndexRepository::test_task_unexpected_error PASSED

==================== 5 passed in 0.3s ====================
```

---

## Definition of Done

- [x] Celery app configured with Redis broker
- [x] `parse_and_index_repository` task implemented
- [x] Retry logic with exponential backoff
- [x] Progress tracking at key stages
- [x] Error handling (validation, storage, unexpected)
- [x] Structured logging with tenant context
- [x] Resource cleanup (storage connections)
- [x] Unit tests (5 test cases)
- [x] Documentation (README with examples)
- [x] Production deployment guides

---

## Integration with Previous Work

### AAET-86: ParserService
- ✅ Celery task wraps `ParserService.parse_repository()`
- ✅ Tenant context flows through entire pipeline
- ✅ Metrics collected and returned

### AAET-85: Async Operations
- ✅ Async/sync bridge using asyncio event loop
- ✅ Proper async storage operations
- ✅ Resource cleanup with finally blocks

### AAET-84: Storage Interface
- ✅ Works with `PostgresGraphStore`
- ✅ Connection management
- ✅ Error handling for storage failures

---

## Next Steps

1. **AAET-88:** Integration Testing
   - End-to-end tests with real Celery worker
   - Multi-tenant isolation tests
   - Load testing

2. **AAET-89:** Documentation
   - API documentation
   - Deployment guides
   - Troubleshooting guides

3. **AAET-91:** Storage Enhancements
   - Batch size limits
   - Type-safe enums
   - Performance optimizations

---

## ✅ AAET-87 COMPLETE!

**Status:** Ready for integration testing and production deployment  
**Branch:** `feature/AAET-87-celery-integration`  
**Next:** Commit changes and create PR
