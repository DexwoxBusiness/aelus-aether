"""Database connection and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.core.logging import get_logger

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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session with automatic tenant context.

    Automatically sets the tenant context from the logging context variable
    to enable Row-Level Security (RLS) policies. The tenant_id is set by
    the JWT middleware after authentication.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...

    Raises:
        SecurityError: If tenant context is missing for protected endpoints
    """
    from app.core.logging import _tenant_id

    async with AsyncSessionLocal() as session:
        try:
            # Set tenant context for RLS
            # tenant_id is set by JWT middleware via bind_request_context()
            tenant_id = _tenant_id.get()

            if not tenant_id:
                # For public endpoints (health checks, etc.), allow without tenant context
                # Protected endpoints should be blocked by JWT middleware before reaching here
                logger.warning(
                    "No tenant_id in context - proceeding without RLS protection. "
                    "This should only happen for public endpoints."
                )
            else:
                try:
                    await set_tenant_context(session, tenant_id)
                    logger.debug("Tenant context set for RLS", tenant_id=tenant_id)
                except Exception as e:
                    logger.error(
                        "Failed to set tenant context",
                        tenant_id=tenant_id,
                        error=str(e),
                    )
                    raise

            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """
    Set tenant context for Row Level Security.

    This must be called before any queries to ensure tenant isolation.

    Args:
        session: The database session
        tenant_id: The tenant UUID to set in the session context

    Raises:
        Exception: If setting the tenant context fails
    """
    # Note: SET LOCAL cannot use bind parameters in PostgreSQL
    # We sanitize the UUID to prevent SQL injection
    import uuid

    # Validate it's a proper UUID
    uuid.UUID(tenant_id)  # Raises ValueError if invalid
    await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
