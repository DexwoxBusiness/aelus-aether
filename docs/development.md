# Development Guide

This guide provides detailed instructions for setting up and developing Aelus-Aether locally.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Development Environment](#development-environment)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [Development Workflow](#development-workflow)
- [Debugging](#debugging)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.12+ | Runtime |
| PostgreSQL | 15+ | Database |
| Redis | 7+ | Cache & Queue |
| Docker | 20+ | Containerization |
| Docker Compose | 2+ | Multi-container orchestration |
| Git | 2+ | Version control |

### Optional Tools

| Tool | Purpose |
|------|---------|
| uv | Fast Python package installer |
| pgAdmin | PostgreSQL GUI |
| Redis Commander | Redis GUI |
| Postman | API testing |

### System Requirements

- **OS**: Linux, macOS, or Windows (WSL2 recommended)
- **RAM**: 8GB minimum, 16GB recommended
- **Disk**: 10GB free space
- **CPU**: 4 cores recommended

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/aelus-aether.git
cd aelus-aether
```

### 2. Install Python Dependencies

**Using uv (Recommended):**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

**Using pip:**
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -e ".[dev]"
```

### 3. Install Pre-commit Hooks

```bash
pre-commit install
```

This will automatically run linting and formatting before each commit.

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

**Required Environment Variables:**

```bash
# Database
DATABASE_URL=postgresql://aelus:aelus_password@localhost:5432/aelus_aether
POSTGRES_USER=aelus
POSTGRES_PASSWORD=aelus_password
POSTGRES_DB=aelus_aether
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# API
SECRET_KEY=your-secret-key-min-32-chars-long
DEBUG=true
LOG_LEVEL=DEBUG

# Voyage AI
VOYAGE_API_KEY=pa-your-api-key-here
```

## Development Environment

### Using Docker Compose (Recommended)

**Start all services:**
```bash
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)

**Check service status:**
```bash
docker-compose ps
```

**View logs:**
```bash
docker-compose logs -f
```

**Stop services:**
```bash
docker-compose down
```

**Reset everything (WARNING: destroys data):**
```bash
docker-compose down -v
```

### Manual Setup (Without Docker)

**Install PostgreSQL:**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql-15 postgresql-contrib-15

# macOS
brew install postgresql@15

# Start service
sudo systemctl start postgresql  # Linux
brew services start postgresql@15  # macOS
```

**Install pgvector extension:**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql-15-pgvector

# macOS
brew install pgvector
```

**Create database:**
```sql
CREATE USER aelus WITH PASSWORD 'aelus_password';
CREATE DATABASE aelus_aether OWNER aelus;
\c aelus_aether
CREATE EXTENSION vector;
```

**Install Redis:**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Start service
sudo systemctl start redis  # Linux
brew services start redis  # macOS
```

## Database Setup

### Run Migrations

```bash
# Apply all migrations
alembic upgrade head

# Or use make command
make migrate-up
```

### Verify Database

```bash
# Connect to database
psql -U aelus -d aelus_aether

# List tables
\dt

# Check pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';

# Exit
\q
```

### Create Test Data

```python
# Run Python shell
python

# Create test tenant
from app.models.tenant import Tenant
from app.core.database import SessionLocal
from uuid import uuid4

async def create_test_data():
    async with SessionLocal() as session:
        tenant = Tenant(
            id=uuid4(),
            name="Test Tenant",
            api_key="test-api-key-123",
            settings={"max_repositories": 10}
        )
        session.add(tenant)
        await session.commit()
        print(f"Created tenant: {tenant.id}")

import asyncio
asyncio.run(create_test_data())
```

## Running the Application

### Start API Server

**Development mode (with auto-reload):**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Production mode:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Using Python module:**
```bash
python -m app.main
```

**Access API:**
- API: http://localhost:8000
- Docs: http://localhost:8000/api/v1/docs
- Health: http://localhost:8000/health

### Start Celery Worker

**Development (single process):**
```bash
celery -A workers.celery_app worker --pool=solo --loglevel=debug
```

**Production (gevent pool):**
```bash
celery -A workers.celery_app worker --pool=gevent --concurrency=100 --loglevel=info
```

**With autoscaling:**
```bash
celery -A workers.celery_app worker --pool=gevent --autoscale=200,50 --loglevel=info
```

**Monitor tasks:**
```bash
# Inspect active tasks
celery -A workers.celery_app inspect active

# Check worker stats
celery -A workers.celery_app inspect stats

# Purge all tasks
celery -A workers.celery_app purge
```

### Start All Services

**Using Make:**
```bash
# Start API server
make run-api

# Start Celery worker
make run-worker

# Start both (in separate terminals)
make run-all
```

**Using Docker Compose:**
```bash
# Start infrastructure only
docker-compose up -d postgres redis

# Run API and worker locally
uvicorn app.main:app --reload &
celery -A workers.celery_app worker --pool=solo --loglevel=info &
```

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/AAET-XX-description
```

### 2. Make Changes

Edit code, add tests, update documentation.

### 3. Run Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_logging.py -v

# With coverage
pytest --cov=app --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### 4. Code Quality Checks

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Fix auto-fixable issues
ruff check --fix .

# Type check
mypy app/ services/ workers/

# Security check
bandit -r app/ services/ workers/
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat(AAET-XX): Add feature description"
```

Pre-commit hooks will automatically run formatting and linting.

### 6. Push and Create PR

```bash
git push origin feature/AAET-XX-description
```

Then create a pull request on GitHub.

## Debugging

### Debug API Server

**Using VS Code:**

Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "jinja": true,
      "justMyCode": false
    }
  ]
}
```

**Using pdb:**
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint()
breakpoint()
```

### Debug Celery Tasks

**Run worker in foreground:**
```bash
celery -A workers.celery_app worker --pool=solo --loglevel=debug
```

**Add breakpoints:**
```python
# In task code
import pdb; pdb.set_trace()
```

**Test task directly:**
```python
from workers.tasks.ingestion import parse_and_index_file

# Call task synchronously (bypasses Celery)
result = await parse_and_index_file(
    tenant_id="test",
    repo_id="test",
    file_path="test.py",
    file_content="def hello(): pass",
    language="python"
)
```

### Debug Database Queries

**Enable SQL logging:**
```python
# In app/core/database.py
engine = create_async_engine(
    settings.database_url,
    echo=True,  # Enable SQL logging
)
```

**Use pgAdmin:**
1. Open pgAdmin
2. Connect to localhost:5432
3. Browse tables and run queries

**Use psql:**
```bash
# Connect
psql -U aelus -d aelus_aether

# View table structure
\d code_nodes

# Run query
SELECT * FROM code_nodes LIMIT 10;

# Explain query
EXPLAIN ANALYZE SELECT * FROM code_nodes WHERE tenant_id = 'xxx';
```

### Debug Redis

**Use redis-cli:**
```bash
# Connect
redis-cli

# List all keys
KEYS *

# Get value
GET key_name

# Monitor commands
MONITOR

# Check memory usage
INFO memory
```

**Use Redis Commander:**
```bash
# Install
npm install -g redis-commander

# Run
redis-commander

# Open browser
http://localhost:8081
```

## Common Tasks

### Add New Database Model

1. **Create model in `app/models/`:**
```python
from sqlalchemy import Column, String
from app.core.database import Base

class NewModel(Base):
    __tablename__ = "new_models"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
```

2. **Create migration:**
```bash
alembic revision --autogenerate -m "Add new_models table"
```

3. **Review migration file** in `migrations/versions/`

4. **Apply migration:**
```bash
alembic upgrade head
```

5. **Add factory in `tests/factories.py`:**
```python
async def create_new_model_async(session, **kwargs):
    defaults = {"id": uuid4(), "name": "Test"}
    defaults.update(kwargs)
    model = NewModel(**defaults)
    session.add(model)
    await session.flush()
    return model
```

### Add New API Endpoint

1. **Create schema in `app/schemas/`:**
```python
from pydantic import BaseModel

class NewModelCreate(BaseModel):
    name: str

class NewModelResponse(BaseModel):
    id: str
    name: str
```

2. **Add endpoint in `app/api/v1/`:**
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter()

@router.post("/new-models", response_model=NewModelResponse)
async def create_new_model(
    data: NewModelCreate,
    db: AsyncSession = Depends(get_db)
):
    # Implementation
    pass
```

3. **Add tests in `tests/api/`:**
```python
@pytest.mark.integration
def test_create_new_model(client):
    response = client.post("/api/v1/new-models", json={"name": "Test"})
    assert response.status_code == 201
```

### Add New Celery Task

1. **Create task in `workers/tasks/`:**
```python
from workers.celery_app import celery_app

@celery_app.task(bind=True, max_retries=3)
async def new_task(self, param1: str):
    # Implementation
    pass
```

2. **Add tests in `tests/workers/`:**
```python
@pytest.mark.asyncio
async def test_new_task():
    result = await new_task("test")
    assert result is not None
```

### Update Dependencies

```bash
# Add new dependency
uv add package-name

# Or edit pyproject.toml and run
uv sync

# Update all dependencies
uv sync --upgrade

# Lock dependencies
uv lock
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows
```

### Database Connection Errors

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list  # macOS

# Check connection
psql -U aelus -d aelus_aether -h localhost

# Reset database
make db-reset
```

### Redis Connection Errors

```bash
# Check Redis is running
redis-cli ping

# Restart Redis
sudo systemctl restart redis  # Linux
brew services restart redis  # macOS
```

### Migration Errors

```bash
# Check current version
alembic current

# View history
alembic history --verbose

# Downgrade one version
alembic downgrade -1

# Stamp version (if out of sync)
alembic stamp head
```

### Celery Worker Not Processing Tasks

```bash
# Check worker is running
celery -A workers.celery_app inspect active

# Check queue depth
redis-cli LLEN celery

# Purge queue
celery -A workers.celery_app purge

# Restart worker with debug logging
celery -A workers.celery_app worker --pool=solo --loglevel=debug
```

### Import Errors

```bash
# Reinstall in development mode
pip install -e ".[dev]"

# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Verify installation
python -c "import app; print(app.__file__)"
```

### Test Failures

```bash
# Run with verbose output
pytest -vv

# Run specific test
pytest tests/test_file.py::test_function -vv

# Show print statements
pytest -s

# Drop into debugger on failure
pytest --pdb
```

## Performance Optimization

### Database Query Optimization

```python
# Use select with specific columns
from sqlalchemy import select

stmt = select(Tenant.id, Tenant.name).where(Tenant.is_active == True)

# Use eager loading for relationships
from sqlalchemy.orm import selectinload

stmt = select(Repository).options(selectinload(Repository.code_nodes))

# Use indexes
# Add index in migration
op.create_index('idx_tenant_id', 'code_nodes', ['tenant_id'])
```

### Caching

```python
from app.utils.cache import cached

@cached(ttl=300, key_prefix="user")
async def get_user(user_id: str):
    # Expensive operation
    return user_data
```

### Batch Processing

```python
# Batch database inserts
from sqlalchemy import insert

stmt = insert(CodeNode).values([
    {"id": "1", "name": "node1"},
    {"id": "2", "name": "node2"},
])
await session.execute(stmt)
```

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [pytest Documentation](https://docs.pytest.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)

## Getting Help

- Check documentation in `docs/` directory
- Search existing JIRA tickets
- Create new JIRA ticket for bugs/features
- Review code comments and docstrings
- Check test files for usage examples
