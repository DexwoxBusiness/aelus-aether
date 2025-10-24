# JWT Authentication

This document describes the JWT authentication system implemented in Aelus-Aether.

## Overview

Aelus-Aether uses JWT (JSON Web Tokens) for stateless authentication with tenant isolation. Every authenticated request must include:
1. A valid JWT token in the `Authorization` header
2. A tenant ID in the `X-Tenant-ID` header that matches the token

## Architecture

### Components

1. **JWT Utilities** (`app/utils/jwt.py`)
   - Token generation with tenant_id claims
   - Token validation and decoding
   - Expiration handling

2. **Authentication Dependencies** (`app/core/auth.py`)
   - FastAPI dependencies for token extraction
   - Tenant validation
   - Request state management

3. **JWT Middleware** (`app/middleware/auth.py`)
   - Automatic authentication for protected endpoints
   - Public endpoint exemption
   - Tenant context injection

## Token Format

JWT tokens contain the following claims:

```json
{
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174001",
  "type": "access",
  "exp": 1234567890,
  "iat": 1234567890
}
```

- `tenant_id` (required): UUID of the tenant
- `user_id` (optional): UUID of the user
- `type`: Token type (always "access")
- `exp`: Expiration timestamp
- `iat`: Issued at timestamp

## Usage

### Creating Tokens

```python
from uuid import UUID
from app.utils.jwt import create_access_token

# Create token with tenant_id
tenant_id = UUID("123e4567-e89b-12d3-a456-426614174000")
token = create_access_token(tenant_id=tenant_id)

# Create token with user_id
user_id = UUID("123e4567-e89b-12d3-a456-426614174001")
token = create_access_token(tenant_id=tenant_id, user_id=user_id)

# Create token with custom expiration
from datetime import timedelta
token = create_access_token(
    tenant_id=tenant_id,
    expires_delta=timedelta(hours=1)
)
```

### Making Authenticated Requests

Include both the JWT token and tenant ID in request headers:

```bash
curl -X GET "http://localhost:8000/api/v1/repositories" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "X-Tenant-ID: 123e4567-e89b-12d3-a456-426614174000"
```

### Using Authentication in Endpoints

Use the `get_current_tenant` dependency to require authentication:

```python
from typing import Annotated
from fastapi import Depends
from app.core.auth import get_current_tenant
from app.models.tenant import Tenant

@app.get("/api/v1/repositories")
async def list_repositories(
    tenant: Annotated[Tenant, Depends(get_current_tenant)]
):
    # tenant is now available and validated
    return tenant.repositories
```

### Optional Authentication

For endpoints that support optional authentication:

```python
from app.core.auth import get_optional_tenant

@app.get("/api/v1/public-data")
async def public_data(
    request: Request,
    tenant: Tenant | None = Depends(get_optional_tenant)
):
    if tenant:
        # Return tenant-specific data
        pass
    else:
        # Return public data
        pass
```

## Public Endpoints

The following endpoints do not require authentication:

- `/` - Root endpoint
- `/health` - Health check
- `/healthz` - Liveness probe
- `/readyz` - Readiness probe
- `/metrics` - Prometheus metrics
- `/api/v1/docs` - API documentation
- `/api/v1/redoc` - ReDoc documentation
- `/api/v1/openapi.json` - OpenAPI schema

## Error Responses

### 401 Unauthorized

Returned when:
- Authorization header is missing
- Authorization header format is invalid
- Token is expired
- Token signature is invalid

```json
{
  "detail": "Token has expired"
}
```

### 400 Bad Request

Returned when:
- X-Tenant-ID header is missing
- X-Tenant-ID format is invalid (not a UUID)

```json
{
  "detail": "Missing X-Tenant-ID header"
}
```

### 403 Forbidden

Returned when:
- Token tenant_id doesn't match X-Tenant-ID header
- Tenant is inactive
- Tenant not found

```json
{
  "detail": "Tenant ID in token does not match X-Tenant-ID header"
}
```

## Security Considerations

1. **Token Storage**: Never store tokens in localStorage. Use httpOnly cookies or secure storage.

2. **Token Expiration**: Default expiration is 24 hours. Configure via `JWT_EXPIRATION_MINUTES` environment variable.

3. **Secret Key**: Use a strong secret key (min 32 characters). Set via `SECRET_KEY` environment variable.

4. **HTTPS**: Always use HTTPS in production to prevent token interception.

5. **Token Rotation**: Implement token refresh mechanism for long-lived sessions.

## Configuration

Authentication settings in `.env`:

```bash
# JWT Configuration
SECRET_KEY=your-secret-key-min-32-characters
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440  # 24 hours

# Tenant Header
TENANT_HEADER_NAME=X-Tenant-ID
```

## Testing

### Unit Tests

Test JWT utilities:
```bash
pytest tests/unit/test_jwt.py -v
```

Test authentication dependencies:
```bash
pytest tests/unit/test_auth_dependencies.py -v
```

### Integration Tests

Test JWT middleware:
```bash
pytest tests/integration/test_jwt_middleware.py -v
```

## Troubleshooting

### Token Expired Error

**Problem**: Getting "Token has expired" error

**Solution**:
- Generate a new token
- Check server time is synchronized (NTP)
- Adjust `JWT_EXPIRATION_MINUTES` if needed

### Tenant Mismatch Error

**Problem**: Getting "Tenant ID in token does not match X-Tenant-ID header"

**Solution**:
- Ensure X-Tenant-ID header matches the tenant_id in the token
- Verify token was generated for the correct tenant

### Invalid Token Error

**Problem**: Getting "Invalid token" error

**Solution**:
- Verify token format is correct (should be JWT)
- Check SECRET_KEY matches between token generation and validation
- Ensure token wasn't tampered with

## Related Documentation

- [Multi-Tenancy](./multi-tenancy.md) - Tenant isolation and management
- [API Reference](./api-reference.md) - Complete API documentation
- [Security](./security.md) - Security best practices
