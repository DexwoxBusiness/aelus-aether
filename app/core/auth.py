"""Authentication dependencies for FastAPI.

This module provides FastAPI dependencies for:
- Extracting and validating JWT tokens
- Validating tenant context
- Providing current tenant to request handlers

Dependencies can be used in route handlers to enforce authentication.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.tenant import Tenant
from app.utils.exceptions import ValidationError
from app.utils.jwt import TokenExpiredError, TokenInvalidError, extract_tenant_id
from app.utils.validation import validate_tenant_exists

logger = get_logger(__name__)


async def get_token_from_header(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """
    Extract JWT token from Authorization header.

    Args:
        authorization: Authorization header value (Bearer <token>)

    Returns:
        str: JWT token

    Raises:
        HTTPException: 401 if header is missing or malformed

    Example:
        Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    """
    if not authorization:
        logger.warning("Missing Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Parse Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning("Invalid Authorization header format")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    logger.debug("Extracted token from Authorization header")
    return token


async def get_tenant_id_from_header(
    x_tenant_id: Annotated[str | None, Header(alias=settings.tenant_header_name)] = None,
) -> UUID:
    """
    Extract tenant ID from X-Tenant-ID header.

    Args:
        x_tenant_id: Tenant ID from header

    Returns:
        UUID: Tenant ID

    Raises:
        HTTPException: 400 if header is missing or invalid UUID format

    Example:
        X-Tenant-ID: 123e4567-e89b-12d3-a456-426614174000
    """
    if not x_tenant_id:
        logger.warning("Missing X-Tenant-ID header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing {settings.tenant_header_name} header",
        )

    try:
        tenant_id = UUID(x_tenant_id)
        logger.debug("Extracted tenant_id from header", tenant_id=str(tenant_id))
        return tenant_id
    except (ValueError, AttributeError) as e:
        logger.warning("Invalid tenant_id format in header", tenant_id=x_tenant_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {settings.tenant_header_name} format. Expected UUID.",
        ) from e


async def validate_token_and_tenant(
    token: Annotated[str, Depends(get_token_from_header)],
    header_tenant_id: Annotated[UUID, Depends(get_tenant_id_from_header)],
) -> UUID:
    """
    Validate JWT token and ensure tenant_id matches header.

    Args:
        token: JWT token from Authorization header
        header_tenant_id: Tenant ID from X-Tenant-ID header

    Returns:
        UUID: Validated tenant ID

    Raises:
        HTTPException: 401 if token is invalid/expired, 403 if tenant mismatch

    Example:
        This dependency ensures:
        1. Token is valid and not expired
        2. Token contains tenant_id claim
        3. Token tenant_id matches X-Tenant-ID header
    """
    try:
        # Extract tenant_id from token
        token_tenant_id = extract_tenant_id(token)

        # Verify tenant_id matches header
        if token_tenant_id != header_tenant_id:
            logger.warning(
                "Tenant ID mismatch",
                token_tenant_id=str(token_tenant_id),
                header_tenant_id=str(header_tenant_id),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant ID in token does not match X-Tenant-ID header",
            )

        logger.debug("Token and tenant validated", tenant_id=str(token_tenant_id))
        return token_tenant_id

    except TokenExpiredError as e:
        logger.warning("Token expired", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except TokenInvalidError as e:
        logger.warning("Invalid token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_tenant(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Tenant:
    """
    Get current authenticated tenant from database.

    This is the main dependency to use in route handlers that require authentication.
    It loads the tenant from database using tenant_id set by middleware.

    Args:
        request: FastAPI request object (contains tenant_id in state)
        db: Database session

    Returns:
        Tenant: Current tenant object

    Raises:
        HTTPException: 401 if not authenticated, 403 if tenant inactive/not found

    Example:
        @app.get("/api/v1/repositories")
        async def list_repositories(
            tenant: Annotated[Tenant, Depends(get_current_tenant)]
        ):
            # tenant is now available and validated
            return tenant.repositories
    """
    # Get tenant_id from request state (set by middleware)
    tenant_id: UUID | None = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        logger.warning("No tenant_id in request state")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        tenant = await validate_tenant_exists(db, tenant_id)

        # Cache tenant in request state for reuse within same request
        request.state.tenant = tenant

        logger.info("Loaded tenant", tenant_id=str(tenant.id), tenant_name=tenant.name)
        return tenant

    except ValidationError as e:
        logger.warning("Tenant validation failed", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e


async def set_tenant_context(request: Request, tenant: Tenant) -> None:
    """
    Set tenant in request state for access throughout request lifecycle.

    Args:
        request: FastAPI request object
        tenant: Current tenant

    Example:
        # In middleware or dependency
        await set_tenant_context(request, tenant)

        # Later in handler
        tenant = request.state.tenant
    """
    request.state.tenant = tenant
    request.state.tenant_id = tenant.id
    logger.debug("Set tenant context in request state", tenant_id=str(tenant.id))


async def get_optional_tenant(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Tenant | None:
    """
    Get tenant from request state if available (for optional auth endpoints).

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        Tenant | None: Tenant if authenticated, None otherwise

    Example:
        @app.get("/api/v1/public-data")
        async def public_data(
            tenant: Tenant | None = Depends(get_optional_tenant)
        ):
            if tenant:
                # Return tenant-specific data
                pass
            else:
                # Return public data
                pass
    """
    # Check if tenant_id is in request state (set by middleware)
    tenant_id: UUID | None = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        return None

    # Check if tenant already loaded in this request
    cached_tenant: Tenant | None = getattr(request.state, "tenant", None)
    if cached_tenant:
        return cached_tenant

    # Load tenant from database
    try:
        tenant = await validate_tenant_exists(db, tenant_id)
        request.state.tenant = tenant
        return tenant
    except ValidationError:
        return None
