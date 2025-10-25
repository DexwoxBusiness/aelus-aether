"""JWT Authentication Middleware.

This middleware validates JWT tokens and tenant context for all authenticated endpoints.
Public endpoints (health checks, docs) are exempted from authentication.

Architecture Note:
- Middleware validates JWT structure, signature, and tenant_id match
- Dependency injection (get_current_tenant) validates tenant exists and is active
- This separation prevents middleware from managing database sessions
- Tenant validation happens lazily only when endpoints actually need the tenant

The middleware:
1. Checks if the endpoint requires authentication
2. Extracts JWT token from Authorization header
3. Validates token signature and expiration
4. Extracts and validates tenant_id from token
5. Validates X-Tenant-ID header matches token
6. Stores tenant_id in request.state for dependency injection

Returns 401 for invalid/missing tokens, 403 for tenant mismatches.
"""

from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.core.auth import (
    get_tenant_id_from_header,
    get_token_from_header,
    validate_token_and_tenant,
)
from app.core.logging import get_logger
from app.utils.jwt import TokenExpiredError, TokenInvalidError

logger = get_logger(__name__)


# Public endpoints that don't require authentication
PUBLIC_PATHS = {
    "/",
    "/health",
    "/healthz",
    "/readyz",
    "/metrics",
    f"{settings.api_prefix}/docs",
    f"{settings.api_prefix}/redoc",
    f"{settings.api_prefix}/openapi.json",
}


def is_public_path(path: str) -> bool:
    """
    Check if a path is public (doesn't require authentication).

    Args:
        path: Request path

    Returns:
        bool: True if path is public, False otherwise
    """
    # Exact match for public paths
    if path in PUBLIC_PATHS:
        return True

    # For docs/openapi paths, check if they match exactly or have trailing slash
    docs_paths = {
        f"{settings.api_prefix}/docs",
        f"{settings.api_prefix}/redoc",
        f"{settings.api_prefix}/openapi.json",
    }
    for docs_path in docs_paths:
        if path == docs_path or path == f"{docs_path}/":
            return True

    # Check root-level public paths (health, metrics)
    root_public = {"/health", "/healthz", "/readyz", "/metrics"}
    for public_path in root_public:
        if path == public_path or path == f"{public_path}/":
            return True

    return False


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    JWT Authentication Middleware.

    Validates JWT tokens and tenant context on all authenticated endpoints.
    Sets tenant in request.state for access in route handlers.

    Public endpoints (health, docs) are exempted from authentication.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process request through authentication middleware.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response: Response from handler or error response
        """
        # Skip authentication for public endpoints
        if is_public_path(request.url.path):
            logger.debug("Public endpoint, skipping auth", path=request.url.path)
            response: Response = await call_next(request)
            return response

        # Log authentication attempt
        logger.debug(
            "Authenticating request",
            path=request.url.path,
            method=request.method,
        )

        try:
            # Use existing auth dependencies to avoid duplication
            token = await get_token_from_header(authorization=request.headers.get("authorization"))
            header_tenant_id = await get_tenant_id_from_header(
                x_tenant_id=request.headers.get(settings.tenant_header_name.lower())
            )
            tenant_id = await validate_token_and_tenant(
                token=token, header_tenant_id=header_tenant_id
            )

            # Store tenant_id in request state for dependency injection
            request.state.tenant_id = tenant_id

            # Bind tenant_id to logging context for RLS and logging
            from app.core.logging import bind_request_context

            bind_request_context(tenant_id=str(tenant_id))

            logger.debug(
                "Request authenticated",
                tenant_id=str(tenant_id),
                path=request.url.path,
            )

            # Continue to next middleware/handler
            return await call_next(request)

        except (
            TokenExpiredError,
            TokenInvalidError,
            HTTPException,
            ValueError,
            AttributeError,
            TypeError,
        ) as e:
            # Handle expected authentication and validation errors
            if isinstance(e, TokenExpiredError):
                logger.warning("Token expired", error=str(e), path=request.url.path)
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Token has expired"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            elif isinstance(e, TokenInvalidError):
                logger.warning("Invalid token", error=str(e), path=request.url.path)
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": f"Invalid token: {e}"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            elif isinstance(e, HTTPException):
                logger.warning(
                    "Authentication failed",
                    status_code=e.status_code,
                    detail=e.detail,
                    path=request.url.path,
                )
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail},
                    headers=e.headers or {},
                )
            else:
                # ValueError, AttributeError, TypeError
                logger.warning(
                    "Invalid request format",
                    error=str(e),
                    error_type=type(e).__name__,
                    path=request.url.path,
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid request format"},
                )

        # This should never be reached, but added for safety
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Authentication flow error"},
        )
