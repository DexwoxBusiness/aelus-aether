"""Database connection and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.core.logging import get_logger


class SecurityError(Exception):
    """Raised when security-critical operations fail (e.g., tenant isolation)."""

    pass


# Public endpoints that don't require tenant context
# These endpoints can access the database without RLS protection
PUBLIC_ENDPOINTS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/health",
}


def is_public_endpoint(path: str | None) -> bool:
    """Check if the given path is a public endpoint that doesn't require tenant context."""
    if not path:
        return False
    # Exact match or starts with public path
    return path in PUBLIC_ENDPOINTS or any(path.startswith(ep) for ep in PUBLIC_ENDPOINTS)


logger = get_logger(__name__)

# Create async engine
engine = create_async_engine(
    settings.db_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Base class for models
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


async def init_db() -> None:
    """Initialize database (create tables if needed)."""
    try:
        async with engine.begin() as conn:
            # Import all models here to ensure they're registered
            from app.models import code_graph, repository, tenant  # noqa: F401

            # Create tables
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
    logger.info("Database engine disposed")


async def get_admin_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for admin operations.

    Admin operations (like creating tenants) don't belong to any tenant,
    so they operate without tenant context. The RLS policies have been
    configured to allow operations on the tenants table when no tenant
    context is set (see admin_bypass_rls migration).

    SECURITY: This should ONLY be used by admin endpoints that have already
    verified admin authentication (X-Admin-Key).

    Usage:
        @router.post("/admin/tenants")
        async def create_tenant(db: AsyncSession = Depends(get_admin_db)):
            # Can create tenants without tenant context
            ...

    Yields:
        AsyncSession: Database session for admin operations
    """
    async with AsyncSessionLocal() as session:
        try:
            # Admin operations work without tenant context
            # RLS policies on tenants table allow NULL tenant_id for admin operations
            logger.info(
                "Admin database session created",
                security_audit=True,
            )

            yield session
            if session.in_transaction():
                await session.commit()
        except Exception:
            if session.in_transaction():
                await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session with automatic tenant context.

    Automatically sets the tenant context from the logging context variable
    to enable Row-Level Security (RLS) policies. The tenant_id is set by
    the JWT middleware after authentication.

    SECURITY: Fail-safe behavior - denies database access if tenant context
    is missing for protected endpoints. Only explicitly allowlisted public
    endpoints can proceed without tenant context.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...

    Raises:
        SecurityError: If tenant context is missing for protected endpoints
    """
    from app.core.logging import _request_path, _tenant_id

    async with AsyncSessionLocal() as session:
        try:
            # Set tenant context for RLS
            # tenant_id is set by JWT middleware via bind_request_context()
            tenant_id = _tenant_id.get()
            request_path = _request_path.get()

            if not tenant_id:
                # SECURITY: Fail-safe behavior - deny access unless explicitly public
                if is_public_endpoint(request_path):
                    # Explicitly allowlisted public endpoint
                    logger.info(
                        "Public endpoint accessed without tenant context",
                        path=request_path,
                        security_audit=True,
                    )
                else:
                    # Protected endpoint without tenant context - DENY ACCESS
                    logger.critical(
                        "CRITICAL: Missing tenant context for protected endpoint - denying database access",
                        path=request_path,
                        security_audit=True,
                    )
                    raise SecurityError(
                        "Tenant isolation failed - missing tenant context. "
                        "This endpoint requires authentication."
                    )
            else:
                try:
                    await set_tenant_context(session, tenant_id)
                    logger.debug("Tenant context set for RLS", tenant_id=tenant_id)
                except (ValueError, DBAPIError, OperationalError) as e:
                    logger.critical(
                        "CRITICAL: Failed to set tenant context - RLS policies will not be enforced",
                        tenant_id=tenant_id,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    # Rollback session immediately on security failure
                    if session.in_transaction():
                        await session.rollback()
                    raise SecurityError("Tenant isolation failed - database access denied") from e

            yield session
            if session.in_transaction():
                await session.commit()
        except SecurityError:
            # Security errors should not commit
            if session.in_transaction():
                await session.rollback()
            raise
        except Exception:
            if session.in_transaction():
                await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_with_tenant(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session with explicit tenant context for background operations.

    This is for use in background jobs, Celery tasks, or any non-HTTP context
    where the tenant_id is known but not in the request context.

    SECURITY: Validates tenant exists and is active before allowing access.
    This prevents background operations on deleted/inactive tenants.

    Args:
        tenant_id: The tenant UUID to set in the session context

    Usage:
        async with get_db_with_tenant(tenant_id) as db:
            # Perform database operations with tenant isolation
            result = await db.execute(...)

    Raises:
        ValueError: If tenant_id is not a valid UUID
        SecurityError: If tenant doesn't exist, is inactive, or context cannot be set
    """
    import uuid

    # Validate UUID format first
    try:
        uuid.UUID(tenant_id)
    except ValueError as e:
        logger.error("Invalid tenant_id format in background operation", tenant_id=tenant_id)
        raise ValueError(f"Invalid tenant_id: must be a valid UUID, got '{tenant_id}'") from e

    async with AsyncSessionLocal() as session:
        try:
            # SECURITY: Verify tenant exists and is active before allowing access
            # This prevents operations on deleted/inactive tenants
            tenant_check = await session.execute(
                text("""
                    SELECT 1 FROM tenants
                    WHERE id = :tenant_id::uuid
                    AND is_active = true
                """),
                {"tenant_id": tenant_id},
            )
            if not tenant_check.scalar():
                logger.error(
                    "Attempted to access non-existent or inactive tenant in background operation",
                    tenant_id=tenant_id,
                    security_audit=True,
                )
                raise SecurityError(
                    f"Tenant {tenant_id} not found or inactive - cannot proceed with background operation"
                )

            await set_tenant_context(session, tenant_id)
            logger.debug("Tenant context set for background operation", tenant_id=tenant_id)
            yield session
            if session.in_transaction():
                await session.commit()
        except (ValueError, DBAPIError, OperationalError) as e:
            logger.critical(
                "CRITICAL: Failed to set tenant context in background operation",
                tenant_id=tenant_id,
                error=str(e),
            )
            if session.in_transaction():
                await session.rollback()
            raise SecurityError("Tenant isolation failed in background operation") from e
        except SecurityError:
            # Security errors should not commit
            if session.in_transaction():
                await session.rollback()
            raise
        except Exception:
            if session.in_transaction():
                await session.rollback()
            raise
        finally:
            await session.close()


async def set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """
    Set tenant context for Row Level Security using PostgreSQL set_config().

    This must be called before any queries to ensure tenant isolation.
    Uses set_config() with parameterized query to prevent SQL injection.

    Args:
        session: The database session
        tenant_id: The tenant UUID to set in the session context

    Raises:
        ValueError: If tenant_id is not a valid UUID
        DBAPIError: If database operation fails
        SecurityError: If tenant context cannot be set (raised by caller)
    """
    import uuid

    # Validate it's a proper UUID before sending to database
    try:
        uuid.UUID(tenant_id)
    except ValueError as e:
        logger.error("Invalid tenant_id format", tenant_id=tenant_id, error=str(e))
        raise ValueError(f"Invalid tenant_id: must be a valid UUID, got '{tenant_id}'") from e

    # Use set_config() with parameterized query to prevent SQL injection
    # set_config(setting_name, new_value, is_local)
    # SECURITY: Use is_local=TRUE (transaction-scoped) so the tenant context
    # is automatically cleared at transaction end and cannot leak between
    # requests when a pooled connection is reused.
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, TRUE)"),
        {"tenant_id": tenant_id},
    )
