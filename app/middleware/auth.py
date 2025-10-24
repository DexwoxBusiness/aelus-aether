"""JWT Authentication Middleware.

This middleware validates JWT tokens and tenant context for all authenticated endpoints.
Public endpoints (health checks, docs) are exempted from authentication.

The middleware:
1. Checks if the endpoint requires authentication
2. Extracts JWT token from Authorization header
3. Validates token signature and expiration
4. Extracts and validates tenant_id from token
5. Validates X-Tenant-ID header matches token
6. Loads tenant from database and sets in request.state

Returns 401 for invalid/missing tokens, 403 for tenant mismatches.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.core.auth import (
    get_tenant_id_from_header,
    get_token_from_header,
    set_tenant_context,
    validate_token_and_tenant,
)
from app.core.database import get_db
from app.core.logging import get_logger
from app.utils.exceptions import ValidationError
from app.utils.jwt import TokenExpiredError, TokenInvalidError
from app.utils.validation import validate_tenant_exists

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

    # Check if path starts with any public prefix
    for public_path in PUBLIC_PATHS:
        if path.startswith(public_path):
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
            # Extract token from Authorization header
            authorization = request.headers.get("authorization")
            if not authorization:
                logger.warning("Missing Authorization header", path=request.url.path)
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Missing Authorization header"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            token = await get_token_from_header(authorization=authorization)

            # Extract tenant_id from X-Tenant-ID header
            x_tenant_id = request.headers.get(settings.tenant_header_name.lower())
            if not x_tenant_id:
                logger.warning("Missing X-Tenant-ID header", path=request.url.path)
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": f"Missing {settings.tenant_header_name} header"},
                )

            header_tenant_id = await get_tenant_id_from_header(x_tenant_id=x_tenant_id)

            # Validate token and tenant_id match
            tenant_id = await validate_token_and_tenant(
                token=token, header_tenant_id=header_tenant_id
            )

            # Get database session and load tenant
            async for db in get_db():
                try:
                    tenant = await validate_tenant_exists(db, tenant_id)

                    # Set tenant in request state
                    await set_tenant_context(request, tenant)

                    logger.info(
                        "Request authenticated",
                        tenant_id=str(tenant.id),
                        tenant_name=tenant.name,
                        path=request.url.path,
                    )

                    # Continue to next middleware/handler
                    handler_response: Response = await call_next(request)
                    return handler_response

                except ValidationError as e:
                    logger.warning(
                        "Tenant validation failed",
                        tenant_id=str(tenant_id),
                        error=str(e),
                        path=request.url.path,
                    )
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": str(e)},
                    )
                finally:
                    await db.close()

        except TokenExpiredError as e:
            logger.warning("Token expired", error=str(e), path=request.url.path)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Token has expired"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        except TokenInvalidError as e:
            logger.warning("Invalid token", error=str(e), path=request.url.path)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": f"Invalid token: {e}"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        except ValueError as e:
            logger.warning("Invalid request format", error=str(e), path=request.url.path)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(e)},
            )
        except Exception as e:
            logger.error(
                "Unexpected error in auth middleware",
                error=str(e),
                error_type=type(e).__name__,
                path=request.url.path,
                exc_info=True,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error during authentication"},
            )

        # This should never be reached, but added for safety
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Authentication flow error"},
        )
