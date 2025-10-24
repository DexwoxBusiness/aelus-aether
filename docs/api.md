# API Documentation

## Base URL

```
Development: http://localhost:8000
Production: https://api.aelus-aether.com (future)
```

## Implementation Status Legend

Throughout this documentation, you'll see status indicators for different API sections:

- ✅ **Implemented** - Endpoint is currently available and functional
- 📋 **Planned** - Endpoint is planned for future implementation, API design may change
- 🚧 **In Progress** - Endpoint is currently being developed

## Authentication

All API requests require a tenant identifier in the header:

```http
X-Tenant-ID: your-tenant-id
```

## Common Headers

### Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `X-Tenant-ID` | Yes | Tenant identifier for multi-tenancy |
| `X-Request-ID` | No | Custom request ID for tracking (auto-generated if not provided) |
| `Content-Type` | Yes (for POST/PUT) | `application/json` |

### Response Headers

| Header | Description |
|--------|-------------|
| `X-Request-ID` | Unique request identifier for tracing |
| `Content-Type` | `application/json` |

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message",
  "request_id": "uuid-here"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing/invalid authentication |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

## Health & Status Endpoints

### GET /health

Liveness probe - checks if application is running.

**Response:**
```json
{
  "status": "healthy"
}
```

### GET /healthz

Alias for `/health`.

### GET /readyz

Readiness probe - checks if application is ready to serve traffic.

**Response (Ready):**
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis": "ok"
  }
}
```

**Response (Not Ready):**
```json
{
  "status": "not_ready",
  "checks": {
    "database": "failed",
    "redis": "ok"
  }
}
```

**Status Code:** 200 (ready) or 503 (not ready)

## Tenant Management

> **Implementation Status:** ✅ Implemented  
> All tenant management endpoints are currently available.

### POST /api/v1/tenants

Create a new tenant.

**Request Body:**
```json
{
  "name": "Acme Corporation",
  "settings": {
    "max_repositories": 10,
    "max_users": 5
  }
}
```

**Response (201):**
```json
{
  "id": "uuid-here",
  "name": "Acme Corporation",
  "api_key": "generated-api-key",
  "settings": {
    "max_repositories": 10,
    "max_users": 5
  },
  "is_active": true,
  "created_at": "2025-10-24T19:00:00Z"
}
```

### GET /api/v1/tenants/{tenant_id}

Get tenant details.

**Response (200):**
```json
{
  "id": "uuid-here",
  "name": "Acme Corporation",
  "settings": {
    "max_repositories": 10,
    "max_users": 5
  },
  "is_active": true,
  "created_at": "2025-10-24T19:00:00Z"
}
```

### GET /api/v1/tenants

List all tenants (admin only).

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | integer | 0 | Number of records to skip |
| `limit` | integer | 100 | Maximum number of records to return |

**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid-1",
      "name": "Tenant 1",
      "is_active": true,
      "created_at": "2025-10-24T19:00:00Z"
    },
    {
      "id": "uuid-2",
      "name": "Tenant 2",
      "is_active": true,
      "created_at": "2025-10-24T19:00:00Z"
    }
  ],
  "total": 2,
  "skip": 0,
  "limit": 100
}
```

## Repository Management

> **Implementation Status:** ✅ Implemented  
> All repository management endpoints are currently available.

### POST /api/v1/repositories

Register a new repository.

**Headers:**
```http
X-Tenant-ID: your-tenant-id
```

**Request Body:**
```json
{
  "name": "backend-api",
  "git_url": "https://github.com/acme/backend-api",
  "branch": "main",
  "language": "python",
  "repo_type": "backend",
  "framework": "fastapi"
}
```

**Response (201):**
```json
{
  "id": "uuid-here",
  "tenant_id": "tenant-uuid",
  "name": "backend-api",
  "git_url": "https://github.com/acme/backend-api",
  "branch": "main",
  "language": "python",
  "repo_type": "backend",
  "framework": "fastapi",
  "sync_status": "pending",
  "last_synced_at": null,
  "created_at": "2025-10-24T19:00:00Z"
}
```

### GET /api/v1/repositories/{repository_id}

Get repository details.

**Headers:**
```http
X-Tenant-ID: your-tenant-id
```

**Response (200):**
```json
{
  "id": "uuid-here",
  "tenant_id": "tenant-uuid",
  "name": "backend-api",
  "git_url": "https://github.com/acme/backend-api",
  "branch": "main",
  "language": "python",
  "sync_status": "completed",
  "last_synced_at": "2025-10-24T19:30:00Z",
  "metadata": {
    "total_files": 150,
    "total_nodes": 1200,
    "total_edges": 3500
  },
  "created_at": "2025-10-24T19:00:00Z"
}
```

### GET /api/v1/repositories

List repositories for tenant.

**Headers:**
```http
X-Tenant-ID: your-tenant-id
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | integer | 0 | Number of records to skip |
| `limit` | integer | 100 | Maximum number of records to return |
| `repo_type` | string | null | Filter by repository type |
| `language` | string | null | Filter by language |

**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid-1",
      "name": "backend-api",
      "language": "python",
      "sync_status": "completed",
      "created_at": "2025-10-24T19:00:00Z"
    },
    {
      "id": "uuid-2",
      "name": "frontend-app",
      "language": "typescript",
      "sync_status": "in_progress",
      "created_at": "2025-10-24T19:05:00Z"
    }
  ],
  "total": 2,
  "skip": 0,
  "limit": 100
}
```

## Ingestion

> **Implementation Status:** ✅ Phase 2 - Implemented  
> These endpoints are currently available and functional.

### POST /api/v1/ingest/repository

Trigger repository ingestion.

**Headers:**
```http
X-Tenant-ID: your-tenant-id
```

**Request Body:**
```json
{
  "repository_id": "repo-uuid",
  "force_refresh": false
}
```

**Response (202):**
```json
{
  "job_id": "job-uuid",
  "status": "queued",
  "repository_id": "repo-uuid",
  "created_at": "2025-10-24T19:00:00Z"
}
```

### GET /api/v1/ingest/job/{job_id}

Get ingestion job status.

**Headers:**
```http
X-Tenant-ID: your-tenant-id
```

**Response (200):**
```json
{
  "job_id": "job-uuid",
  "status": "in_progress",
  "repository_id": "repo-uuid",
  "progress": {
    "files_processed": 45,
    "files_total": 150,
    "nodes_created": 540,
    "edges_created": 1620,
    "embeddings_created": 2700
  },
  "started_at": "2025-10-24T19:00:00Z",
  "updated_at": "2025-10-24T19:05:00Z"
}
```

**Job Statuses:**
- `queued` - Job is in queue
- `in_progress` - Job is being processed
- `completed` - Job completed successfully
- `failed` - Job failed with errors
- `cancelled` - Job was cancelled

## Retrieval

> **Implementation Status:** 📋 Phase 4 - Planned  
> These endpoints are planned for future implementation. API design is subject to change.

### POST /api/v1/retrieve/search

Hybrid search across code graph.

**Headers:**
```http
X-Tenant-ID: your-tenant-id
```

**Request Body:**
```json
{
  "query": "authentication middleware implementation",
  "repository_ids": ["repo-uuid-1", "repo-uuid-2"],
  "filters": {
    "language": "python",
    "node_type": "Function"
  },
  "top_k": 10,
  "include_context": true
}
```

**Response (200):**
```json
{
  "results": [
    {
      "node_id": "node-uuid",
      "qualified_name": "app.middleware.auth.authenticate",
      "node_type": "Function",
      "file_path": "app/middleware/auth.py",
      "start_line": 45,
      "end_line": 78,
      "score": 0.95,
      "source_code": "async def authenticate(request: Request):\n    ...",
      "context": {
        "imports": ["fastapi", "jwt"],
        "calls": ["verify_token", "get_user"],
        "called_by": ["main_middleware"]
      }
    }
  ],
  "total": 10,
  "query_time_ms": 150
}
```

### POST /api/v1/retrieve/graph

Graph traversal query.

**Headers:**
```http
X-Tenant-ID: your-tenant-id
```

**Request Body:**
```json
{
  "start_node": "node-uuid",
  "edge_types": ["CALLS", "IMPORTS"],
  "direction": "outgoing",
  "max_depth": 3,
  "limit": 50
}
```

**Response (200):**
```json
{
  "nodes": [
    {
      "id": "node-uuid-1",
      "qualified_name": "module.function1",
      "node_type": "Function",
      "depth": 1
    },
    {
      "id": "node-uuid-2",
      "qualified_name": "module.function2",
      "node_type": "Function",
      "depth": 2
    }
  ],
  "edges": [
    {
      "from_node_id": "node-uuid",
      "to_node_id": "node-uuid-1",
      "edge_type": "CALLS"
    },
    {
      "from_node_id": "node-uuid-1",
      "to_node_id": "node-uuid-2",
      "edge_type": "CALLS"
    }
  ],
  "total_nodes": 2,
  "total_edges": 2
}
```

## Rate Limiting

Rate limits are enforced per tenant:

- **API Requests**: 100 requests per minute
- **Ingestion Jobs**: 10 concurrent jobs
- **Search Queries**: 50 queries per minute

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1698163200
```

**Rate Limit Exceeded (429):**
```json
{
  "detail": "Rate limit exceeded. Try again in 30 seconds.",
  "retry_after": 30
}
```

## Pagination

List endpoints support cursor-based pagination:

**Request:**
```http
GET /api/v1/repositories?skip=0&limit=50
```

**Response:**
```json
{
  "items": [...],
  "total": 150,
  "skip": 0,
  "limit": 50,
  "has_more": true
}
```

## Filtering & Sorting

**Filtering:**
```http
GET /api/v1/repositories?language=python&repo_type=backend
```

**Sorting:**
```http
GET /api/v1/repositories?sort_by=created_at&sort_order=desc
```

## Webhooks

> **Implementation Status:** 📋 Future - Planned  
> Webhook functionality is planned for a future release.

Configure webhooks to receive notifications:

**Events:**
- `repository.ingestion.completed`
- `repository.ingestion.failed`
- `tenant.quota.exceeded`

**Webhook Payload:**
```json
{
  "event": "repository.ingestion.completed",
  "tenant_id": "tenant-uuid",
  "data": {
    "repository_id": "repo-uuid",
    "job_id": "job-uuid",
    "stats": {
      "nodes_created": 1200,
      "edges_created": 3500
    }
  },
  "timestamp": "2025-10-24T19:30:00Z"
}
```

## SDK Examples

### Python

```python
import asyncio
import httpx

class AelusAetherClient:
    def __init__(self, base_url: str, tenant_id: str):
        self.base_url = base_url
        self.tenant_id = tenant_id
        self.client = httpx.AsyncClient()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def create_repository(self, data: dict):
        response = await self.client.post(
            f"{self.base_url}/api/v1/repositories",
            json=data,
            headers={"X-Tenant-ID": self.tenant_id}
        )
        response.raise_for_status()
        return response.json()

    async def search(self, query: str, top_k: int = 10):
        response = await self.client.post(
            f"{self.base_url}/api/v1/retrieve/search",
            json={"query": query, "top_k": top_k},
            headers={"X-Tenant-ID": self.tenant_id}
        )
        response.raise_for_status()
        return response.json()

# Usage
async def main():
    client = AelusAetherClient("http://localhost:8000", "tenant-123")
    try:
        results = await client.search("authentication middleware")
        print(results)
    finally:
        await client.close()

# Run
asyncio.run(main())
```

### cURL

```bash
# Create repository
curl -X POST http://localhost:8000/api/v1/repositories \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tenant-123" \
  -d '{
    "name": "backend-api",
    "git_url": "https://github.com/acme/backend-api",
    "language": "python"
  }'

# Search
curl -X POST http://localhost:8000/api/v1/retrieve/search \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tenant-123" \
  -d '{
    "query": "authentication middleware",
    "top_k": 10
  }'
```

## Interactive API Documentation

Visit the auto-generated interactive API documentation:

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **OpenAPI Schema**: http://localhost:8000/api/v1/openapi.json

## Versioning

API versioning is done via URL path:

- Current: `/api/v1/`
- Future: `/api/v2/` (when breaking changes are introduced)

## Deprecation Policy

- Deprecated endpoints will be supported for at least 6 months
- Deprecation warnings will be included in response headers
- Migration guides will be provided

## Support

For API support:
- Documentation: This file
- Issues: Create JIRA ticket
- Email: support@aelus-aether.com (future)
