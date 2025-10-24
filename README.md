# Aelus-Aether

**Multi-tenant, multi-repository RAG system for product intelligence**

## Overview

Aelus-Aether is a production-ready SaaS platform that provides deep code understanding and product intelligence by:

- 🔍 **Multi-language parsing** using code-graph-rag (9 languages supported)
- 🌐 **Multi-repo understanding** across frontend, backend, and docs
- 🔐 **Multi-tenant isolation** with Row Level Security
- 🚀 **Hybrid search** combining vector + graph retrieval
- 📊 **Product intelligence** mapping user stories to code

## Architecture

Built on:
- **FastAPI** - Modern async web framework
- **PostgreSQL + pgvector** - Relational + vector + graph storage
- **Redis** - Task queue and caching
- **Celery** - Async background workers
- **code-graph-rag** - Multi-language AST parsing library
- **Voyage AI** - Code embeddings (voyage-code-3, 1024-d vectors)

See [AELUS_AETHER_ARCHITECTURE.md](../AELUS_AETHER_ARCHITECTURE.md) for complete architecture details.

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 15+ with pgvector extension
- Redis 7+
- Docker & Docker Compose (optional)

### Installation

1. **Clone the repository:**
```bash
cd aelus-aether
```

2. **Install dependencies:**
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .

# For Celery workers with async support (production)
pip install -e ".[workers]"
```

3. **Setup environment:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

**Required Environment Variables:**
```bash
# Database
DATABASE_URL=postgresql://aelus:aelus_password@localhost:5432/aelus_aether

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Voyage AI (for embeddings)
VOYAGE_API_KEY=pa-your-api-key-here
```

**Getting Voyage AI API Key:**
1. Sign up at [https://www.voyageai.com/](https://www.voyageai.com/)
2. Navigate to API Keys section
3. Create a new API key
4. Copy the key (starts with `pa-...`) and add to `.env`

4. **Start services with Docker:**
```bash
docker-compose up -d
```

5. **Run database migrations:**
```bash
# Apply all migrations
alembic upgrade head

# Or use make command
make migrate-up
```

6. **Start the API server:**
```bash
python -m app.main
# Or with uvicorn
uvicorn app.main:app --reload
```

7. **Start Celery workers:**

**For Development:**
```bash
# Install gevent for async task support
pip install gevent

# Start worker with solo pool (single process, good for debugging)
celery -A workers.celery_app worker --pool=solo --loglevel=info
```

**For Production:**
```bash
# Install gevent for high concurrency
pip install gevent

# Start worker with gevent pool (recommended for async tasks)
celery -A workers.celery_app worker --pool=gevent --concurrency=100 --loglevel=info

# Or with autoscaling
celery -A workers.celery_app worker --pool=gevent --autoscale=200,50 --loglevel=info
```

**Important Notes:**
- ⚠️ **DO NOT use `--pool=prefork`** (default) with async tasks - it will block
- ✅ Use `--pool=solo` for development/debugging
- ✅ Use `--pool=gevent` or `--pool=eventlet` for production
- 📦 Requires: `celery>=5.5.0` and `gevent` or `eventlet`

8. **Access the API:**
- API: http://localhost:8000
- Docs: http://localhost:8000/api/v1/docs
- Health (liveness): http://localhost:8000/health or http://localhost:8000/healthz
- Readiness: http://localhost:8000/readyz

## Database Migrations

Aelus-Aether uses **Alembic** for database schema migrations.

### Common Migration Commands

```bash
# View current migration status
alembic current

# View migration history
alembic history --verbose

# Upgrade to latest version
alembic upgrade head

# Upgrade one version
alembic upgrade +1

# Downgrade one version
alembic downgrade -1

# Create a new migration (manual)
alembic revision -m "description of changes"

# Create a new migration (autogenerate from models)
alembic revision --autogenerate -m "description"
```

### Using Make Commands

```bash
# Apply migrations
make migrate-up

# Rollback last migration
make migrate-down

# Create new migration
make migrate-create

# Reset database (WARNING: destroys all data)
make db-reset
```

### Migration Files

- **Location:** `migrations/versions/`
- **001_initial_schema.py** - Initial code graph tables (deprecated)
- **002_tenant_schema_complete.py** - Complete tenant schema with security (AAET-15)
  - Creates: tenants, users, repositories tables
  - Updates: code_nodes, code_edges, code_embeddings with proper FKs
  - Implements: Multi-tenant isolation, API key hashing, cascade deletes
- **Configuration:** `alembic.ini` - Alembic configuration file

### Tenant Schema (AAET-15)

**Multi-Tenant Architecture:**
- **Tenants** - Organizations with isolated data and quotas
- **Users** - Members belonging to tenants with role-based access
- **Repositories** - Code repositories owned by tenants
- **Code Graph** - Nodes, edges, and embeddings isolated by tenant_id

**Security Features:**
- ✅ **API Key Hashing** - Keys hashed with bcrypt (cost factor 12), never stored in plaintext
- ✅ **Password Hashing** - User passwords hashed with bcrypt
- ✅ **Secure Generation** - Cryptographically secure random key generation
- ✅ **Cascade Deletes** - Deleting tenant removes all related data automatically

**Tenant Quotas (JSONB):**
```json
{
  "vectors": 500000,      // Max vector embeddings
  "qps": 50,              // Queries per second limit
  "storage_gb": 100,      // Storage limit in GB
  "repos": 10             // Max repositories
}
```

**Multi-Tenant Isolation:**
- All queries automatically filtered by `tenant_id`
- Cache keys prefixed: `{tenant_id}:{resource}:{key}`
- Rate limits per-tenant: `{tenant_id}:ratelimit:{resource}`
- Foreign key constraints enforce data integrity

## Redis Configuration

Aelus-Aether uses **Redis** for multiple purposes with separate database numbers:

- **DB 0**: Queue (Celery broker and result backend)
- **DB 1**: Cache (application caching)
- **DB 2**: Rate Limiting (rate limit counters)

### Connection Pooling

- **Max Connections**: 50 per client
- **Health Checks**: Automatic health checks every 30 seconds
- **Socket Keepalive**: Enabled for connection stability
- **Connection Timeout**: 5 seconds

### Usage Examples

**Caching:**
```python
from app.utils.cache import cache

# Set cache
await cache.set("user:123", "John Doe", ttl=3600)

# Get cache
value = await cache.get("user:123")

# JSON caching
await cache.set_json("user:123", {"name": "John", "age": 30})
data = await cache.get_json("user:123")

# Decorator-based caching
from app.utils.cache import cached

@cached(ttl=300, key_prefix="user")
async def get_user(user_id: str):
    return {"id": user_id, "name": "John"}
```

**Rate Limiting:**
```python
from app.utils.rate_limit import rate_limiter

# Check rate limit (100 requests per minute)
allowed, remaining = await rate_limiter.check_rate_limit(
    key=f"user:{user_id}",
    max_requests=100,
    window_seconds=60
)

if not allowed:
    raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

## API Features

### Request Tracking

Every request is automatically assigned a unique **Request ID** (X-Request-ID header):

- **Automatic Generation**: If no X-Request-ID header is provided, one is generated
- **Propagation**: Request ID is included in all logs and returned in response headers
- **Client Tracking**: Clients can provide their own X-Request-ID for end-to-end tracing

```bash
# Example: Make request with custom request ID
curl -H "X-Request-ID: my-custom-id-123" http://localhost:8000/health

# Response will include:
# X-Request-ID: my-custom-id-123
```

### Health Checks

**Liveness Probe** (`/health` or `/healthz`):
- Returns 200 if application is running
- Does not check dependencies
- Use for Kubernetes liveness probes

**Readiness Probe** (`/readyz`):
- Returns 200 if application is ready to serve traffic
- Checks database connectivity
- Returns 503 if not ready
- Use for Kubernetes readiness probes

## Development

### Project Structure

```
aelus-aether/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── tenants.py          # Tenant management
│   │       ├── repositories.py     # Repository management
│   │       ├── ingestion.py        # Ingestion endpoints
│   │       └── retrieval.py        # Search endpoints
│   ├── core/
│   │   └── database.py             # Database connection
│   ├── models/
│   │   ├── tenant.py               # Tenant & User models
│   │   ├── repository.py           # Repository model
│   │   └── code_graph.py           # Code nodes/edges/embeddings
│   ├── schemas/
│   │   └── ...                     # Pydantic schemas
│   ├── services/
│   │   └── ...                     # Business logic (Phase 2)
│   ├── config.py                   # Configuration
│   └── main.py                     # FastAPI app
├── libs/
│   └── code_graph_rag/             # Extracted library (AAET-82)
├── tests/
│   └── ...                         # Tests
├── migrations/
│   └── ...                         # Alembic migrations
├── docker-compose.yaml
├── pyproject.toml
└── README.md
```

### Running Tests

Aelus-Aether uses **pytest** with comprehensive fixtures for testing.

**Run all tests:**
```bash
pytest
```

**Run with coverage:**
```bash
pytest --cov=app --cov-report=html
```

**Run specific test types:**
```bash
# Unit tests only (fast, no external dependencies)
pytest -m unit

# Integration tests only (require DB/Redis)
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

**Run specific test file:**
```bash
pytest tests/test_logging.py -v
```

**Test Fixtures Available:**
- `db_session` - Async database session with automatic rollback
- `redis_client` - Redis client with automatic cleanup
- `client` - FastAPI TestClient
- `factories` - Test data factories (tenants, users, repositories, code nodes)

**Example Test:**
```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_tenant(db_session, factories):
    # Create test tenant using factory
    tenant = factories.create_tenant(name="Test Company")

    assert tenant.id is not None
    assert tenant.name == "Test Company"
```

**Test Data Factories:**
```python
# Create tenant with users
tenant, users = factories.create_tenant_with_users(user_count=5)

# Create repository with code nodes
repository, nodes = factories.create_repository_with_nodes(node_count=10)

# Create complete code graph
repository, nodes, edges = factories.create_complete_code_graph(
    node_count=10, edge_count=15
)
```

### Code Quality

**Pre-commit Hooks (Recommended):**
```bash
# Install pre-commit hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Update hooks to latest versions
pre-commit autoupdate
```

**Manual Checks:**
```bash
# Linting
ruff check .

# Type checking
mypy app/

# Format
ruff format .

# Security checks
bandit -r app/ services/ workers/
```

## Embeddings & RAG

### Voyage AI Integration

Aelus-Aether uses **Voyage AI's voyage-code-3 model** for generating code embeddings:

- **Model**: voyage-code-3 (optimized for code)
- **Dimensions**: 1024-d vectors
- **Batch Size**: Up to 96 chunks per API request
- **Rate Limiting**: 1 second delay between batches
- **Retry Logic**: Automatic retry with exponential backoff for 429/500/503 errors

### Features

- ✅ **Automatic batching** - Handles large codebases efficiently
- ✅ **Rate limiting** - Prevents API throttling
- ✅ **Error handling** - Graceful handling of API errors with retries
- ✅ **Progress tracking** - Real-time status updates via Celery
- ✅ **Partial failure handling** - Continues processing even if some batches fail

### Storage

Embeddings are stored in PostgreSQL using **pgvector extension**:
- Vector similarity search with IVFFlat index
- Cosine distance for semantic similarity
- Multi-tenant isolation at database level

## API Endpoints

### Tenants
- `POST /api/v1/tenants` - Create tenant
- `GET /api/v1/tenants/{id}` - Get tenant
- `GET /api/v1/tenants` - List tenants

### Repositories
- `POST /api/v1/repositories` - Register repository
- `GET /api/v1/repositories/{id}` - Get repository
- `GET /api/v1/repositories` - List repositories

### Ingestion (Phase 2)
- `POST /api/v1/ingest/repository` - Trigger ingestion
- `GET /api/v1/ingest/job/{id}` - Get job status

### Retrieval (Phase 4)
- `POST /api/v1/retrieve/search` - Hybrid search

## Implementation Status

### ✅ Phase 1: Scaffolding
- [x] FastAPI application setup
- [x] Database models (tenants, repos, code graph)
- [x] Basic API endpoints
- [x] code-graph-rag library extraction (AAET-82)
- [x] Tenant context infrastructure (AAET-83)
- [x] Storage interface with PostgreSQL (AAET-84)
- [x] Async operations (AAET-85)

### ✅ Phase 2: Ingestion (Current)
- [x] Parser service (AAET-86)
- [x] Celery tasks with async support (AAET-87)
- [x] Voyage AI embeddings integration (AAET-87)
- [x] Storage layer with pgvector (AAET-87)
- [x] Batch processing & rate limiting (AAET-87)
- [x] Retry logic & error handling (AAET-87)

### 📋 Phase 3: Multi-Repo (Weeks 9-12)
- [ ] Cross-repo linking
- [ ] API endpoint detection
- [ ] Frontend-backend mapping

### 📋 Phase 4: Retrieval (Weeks 13-16)
- [ ] Hybrid search
- [ ] Reranking
- [ ] Query optimization

## Documentation

### Quick Links

- **[Contributing Guide](CONTRIBUTING.md)** - Development workflow and guidelines
- **[Architecture Overview](docs/architecture.md)** - System design and components
- **[API Documentation](docs/api.md)** - Complete API reference
- **[Development Guide](docs/development.md)** - Detailed setup and debugging

### Additional Resources

- [Architecture](../AELUS_AETHER_ARCHITECTURE.md)
- [JIRA Updates](../JIRA_UPDATES_SUMMARY.md)
- [Quick Start Guide](../QUICK_START_GUIDE.md)

## Contributing

We welcome contributions! Please read our [Contributing Guide](CONTRIBUTING.md) for:

- Development setup
- Code standards
- Testing guidelines
- Pull request process
- Git workflow

## License

MIT License - see [LICENSE](../LICENSE)

## Support

For questions or issues, please create a JIRA ticket in the aelus-aether project.
