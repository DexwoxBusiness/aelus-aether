# Aelus-Aether Setup Guide

## Phase 1: FastAPI Scaffolding ✅

This guide will help you set up the aelus-aether development environment.

---

## Prerequisites

- **Python 3.12+** - [Download](https://www.python.org/downloads/)
- **PostgreSQL 15+** - [Download](https://www.postgresql.org/download/) or use Docker
- **Redis 7+** - [Download](https://redis.io/download) or use Docker
- **Docker & Docker Compose** (recommended) - [Download](https://www.docker.com/products/docker-desktop/)
- **uv** (Python package manager) - `pip install uv`

---

## Quick Setup (Recommended)

### 1. Clone and Navigate

```bash
cd aelus-aether
```

### 2. Install Dependencies

```bash
# Install uv if you haven't
pip install uv

# Install project dependencies
make dev
```

### 3. Setup Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# At minimum, set:
# - SECRET_KEY (generate with: openssl rand -hex 32)
# - POSTGRES_PASSWORD
```

### 4. Start Services

```bash
# Start PostgreSQL and Redis with Docker
make docker-up

# Verify services are running
docker ps
```

### 5. Initialize Database

```bash
# Create tables (using SQLAlchemy for now, Alembic migrations coming soon)
# Tables will be auto-created on first run
```

### 6. Run the Application

```bash
# Start FastAPI development server
make run

# Or manually:
python -m app.main
```

### 7. Verify Installation

Open your browser:
- **API Docs:** http://localhost:8000/api/v1/docs
- **Health Check:** http://localhost:8000/health
- **Root:** http://localhost:8000/

You should see the Swagger UI with all available endpoints!

---

## Manual Setup (Without Docker)

### 1. Install PostgreSQL

```bash
# macOS
brew install postgresql@15

# Ubuntu/Debian
sudo apt-get install postgresql-15 postgresql-contrib

# Start PostgreSQL
brew services start postgresql@15  # macOS
sudo systemctl start postgresql     # Linux
```

### 2. Install pgvector Extension

```bash
# macOS
brew install pgvector

# Ubuntu/Debian
sudo apt-get install postgresql-15-pgvector

# Enable extension
psql -U postgres -c "CREATE EXTENSION vector;"
```

### 3. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database and user
CREATE DATABASE aelus_aether;
CREATE USER aelus WITH PASSWORD 'aelus_password';
GRANT ALL PRIVILEGES ON DATABASE aelus_aether TO aelus;

# Enable extensions
\c aelus_aether
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
\q
```

### 4. Install Redis

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis
```

### 5. Update .env

```bash
# Edit .env to use local services
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 6. Run Application

```bash
make run
```

---

## Testing the API

### Create a Tenant

```bash
curl -X POST "http://localhost:8000/api/v1/tenants" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Company",
    "api_key": "test-api-key-12345678901234567890",
    "quotas": {"vectors": 100000, "qps": 10, "repos": 5}
  }'
```

### Create a Repository

```bash
curl -X POST "http://localhost:8000/api/v1/repositories" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "<tenant-id-from-above>",
    "name": "backend-api",
    "git_url": "https://github.com/yourorg/backend-api",
    "branch": "main",
    "repo_type": "backend",
    "framework": "fastapi",
    "language": "python"
  }'
```

### List Tenants

```bash
curl "http://localhost:8000/api/v1/tenants"
```

---

## Development Workflow

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# View coverage report
open htmlcov/index.html
```

### Code Quality

```bash
# Lint code
make lint

# Format code
make format

# Run all checks
make check
```

### Database Operations

```bash
# View Docker logs
make docker-logs

# Stop services
make docker-down

# Reset database (WARNING: destroys data)
make db-reset
```

---

## Project Structure

```
aelus-aether/
├── app/
│   ├── api/v1/              # API endpoints
│   │   ├── tenants.py       # ✅ Working
│   │   ├── repositories.py  # ✅ Working
│   │   ├── ingestion.py     # 🚧 Phase 2
│   │   └── retrieval.py     # 🚧 Phase 4
│   ├── core/
│   │   └── database.py      # ✅ Database connection
│   ├── models/              # ✅ SQLAlchemy models
│   ├── schemas/             # ✅ Pydantic schemas
│   ├── config.py            # ✅ Configuration
│   └── main.py              # ✅ FastAPI app
├── libs/
│   └── code_graph_rag/      # 🚧 AAET-82 (extract library)
├── tests/                   # ✅ Basic tests
├── docker-compose.yaml      # ✅ Docker services
├── pyproject.toml           # ✅ Dependencies
└── Makefile                 # ✅ Common tasks
```

---

## Next Steps

### Phase 1 Completion (This Week)

- [ ] **AAET-82:** Extract code-graph-rag library
  - Copy parsers from `../codebase_rag/parsers/`
  - Copy language_config.py, schemas.py
  - Refactor graph_updater.py → graph_builder.py

- [ ] **Setup Alembic migrations**
  ```bash
  make migrate-init
  make migrate-create
  make migrate-up
  ```

- [ ] **Add more tests**
  - Test tenant creation
  - Test repository creation
  - Test database models

### Phase 2: Ingestion (Weeks 3-4)

- [ ] **AAET-83:** Add tenant context to library
- [ ] **AAET-84:** Abstract storage interface
- [ ] **AAET-85:** Convert to async
- [ ] **AAET-86:** Build parser service
- [ ] **AAET-87:** Celery integration

---

## Troubleshooting

### PostgreSQL Connection Error

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# View logs
docker logs aelus-postgres

# Restart service
make docker-down && make docker-up
```

### Redis Connection Error

```bash
# Check if Redis is running
docker ps | grep redis

# Test connection
redis-cli ping
# Should return: PONG
```

### Import Errors

```bash
# Reinstall dependencies
make clean
make dev
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

---

## Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | JWT secret key | - | ✅ |
| `POSTGRES_HOST` | PostgreSQL host | localhost | ✅ |
| `POSTGRES_PORT` | PostgreSQL port | 5432 | ✅ |
| `POSTGRES_USER` | PostgreSQL user | aelus | ✅ |
| `POSTGRES_PASSWORD` | PostgreSQL password | - | ✅ |
| `POSTGRES_DB` | Database name | aelus_aether | ✅ |
| `REDIS_HOST` | Redis host | localhost | ✅ |
| `REDIS_PORT` | Redis port | 6379 | ✅ |
| `VOYAGE_API_KEY` | Voyage AI API key | - | Phase 2 |
| `COHERE_API_KEY` | Cohere API key | - | Phase 4 |

---

## Support

- **Architecture:** See [AELUS_AETHER_ARCHITECTURE.md](../AELUS_AETHER_ARCHITECTURE.md)
- **JIRA:** Check [JIRA_UPDATES_SUMMARY.md](../JIRA_UPDATES_SUMMARY.md)
- **Quick Start:** See [QUICK_START_GUIDE.md](../QUICK_START_GUIDE.md)

---

**Status:** ✅ Phase 1 Scaffolding Complete - Ready for AAET-82 (Library Extraction)
