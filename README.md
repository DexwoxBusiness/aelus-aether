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
# Coming in Phase 1 - Alembic migrations
alembic upgrade head
```

6. **Start the API server:**
```bash
python -m app.main
# Or with uvicorn
uvicorn app.main:app --reload
```

7. **Access the API:**
- API: http://localhost:8000
- Docs: http://localhost:8000/api/v1/docs
- Health: http://localhost:8000/health

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

```bash
pytest
# With coverage
pytest --cov=app
```

### Code Quality

```bash
# Linting
ruff check .

# Type checking
mypy app/

# Format
ruff format .
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

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.

## License

MIT License - see [LICENSE](../LICENSE)

## Documentation

- [Architecture](../AELUS_AETHER_ARCHITECTURE.md)
- [JIRA Updates](../JIRA_UPDATES_SUMMARY.md)
- [Quick Start Guide](../QUICK_START_GUIDE.md)

## Support

For questions or issues, please create a JIRA ticket in the aelus-aether project.
