"""Pytest configuration and fixtures for Aelus-Aether tests.

This module provides centralized test fixtures for:
- Database sessions (with automatic cleanup)
- Redis clients (with automatic cleanup)
- FastAPI TestClient
- Test data factories
- Async support
"""

from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.core.database import get_db
from app.main import app

# ============================================================================
# Test Database Configuration
# ============================================================================


def get_test_database_url(base_url: str, test_suffix: str = "_test") -> str:
    """
    Generate test database URL from base URL.

    Uses proper URL parsing to avoid brittle string manipulation.
    """
    url = make_url(base_url)
    test_db_name = f"{url.database}{test_suffix}"
    url = url.set(database=test_db_name)
    return str(url)


def get_postgres_admin_url(base_url: str) -> str:
    """Get PostgreSQL admin URL (postgres database) for creating test databases."""
    url = make_url(base_url)
    url = url.set(database="postgres")
    return str(url)


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (require DB/Redis)")
    config.addinivalue_line("markers", "slow: Slow tests (may take >5 seconds)")
    config.addinivalue_line("markers", "asyncio: Async tests")


# ============================================================================
# Database Fixtures
# ============================================================================
# Note: Event loop is automatically managed by pytest-asyncio with asyncio_mode = "auto"


@pytest.fixture(scope="session")
def test_db_engine():
    """
    Create test database engine (session-scoped).

    Creates a fresh test database for the entire test session.
    Uses unique database name to support concurrent test runs.
    """
    import os
    import uuid

    # Generate unique database name for this test session
    # Supports concurrent CI runs without conflicts
    test_run_id = os.getenv("PYTEST_XDIST_WORKER", uuid.uuid4().hex[:8])
    test_suffix = f"_test_{test_run_id}"

    # Generate test database URLs using proper URL parsing
    # Build URL directly from individual config values to ensure credentials are correct
    base_url = (
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    test_db_url = get_test_database_url(base_url, test_suffix)
    test_db_url_async = test_db_url.replace("postgresql://", "postgresql+asyncpg://")

    # Extract test database name for validation
    test_db_name = make_url(test_db_url).database

    # Create synchronous engine for database creation and admin tasks
    admin_url = get_postgres_admin_url(base_url)
    sync_engine = create_engine(
        admin_url,
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )

    try:
        # Drop and recreate test database
        with sync_engine.connect() as conn:
            # Terminate existing connections to the test database
            conn.execute(
                text("""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = :db_name
                    AND pid <> pg_backend_pid()
                """),
                {"db_name": test_db_name},
            )
            # Note: Database names cannot be parameterized in DDL statements
            # Using identifier() would be ideal but text() doesn't support it
            # Validate database name format to prevent injection
            if not test_db_name.replace("_", "").replace("-", "").isalnum():
                raise ValueError(f"Invalid test database name format: {test_db_name}")
            conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
            conn.execute(text(f"CREATE DATABASE {test_db_name}"))

            # Create or reset non-superuser test role for application queries
            test_role = "aelus_test"
            test_role_password = "aelus_test_password"
            conn.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT FROM pg_roles WHERE rolname = :role_name
                        ) THEN
                            CREATE ROLE """
                    + test_role
                    + """ LOGIN PASSWORD :role_pass;
                        ELSE
                            ALTER ROLE """
                    + test_role
                    + """ WITH LOGIN PASSWORD :role_pass;
                        END IF;
                    END
                    $$;
                    """
                ),
                {"role_name": test_role, "role_pass": test_role_password},
            )

            # Grant privileges on the new database to the test role
            conn.execute(text(f'GRANT ALL PRIVILEGES ON DATABASE {test_db_name} TO "{test_role}"'))
    except Exception as e:
        sync_engine.dispose()
        raise RuntimeError(f"Failed to create test database: {e}") from e
    finally:
        sync_engine.dispose()

    # Run migrations and extension creation using admin sync connection on the test database
    # Then create async engine for tests using a non-superuser role to ensure RLS is enforced
    test_sync_engine = create_engine(
        test_db_url,
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )

    try:
        # 1) Ensure vector extension exists (admin context)
        with test_sync_engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

            # 2) Run Alembic migrations with this connection
            from alembic import command
            from alembic.config import Config

            alembic_cfg = Config("alembic.ini")
            alembic_cfg.attributes["connection"] = conn
            command.upgrade(alembic_cfg, "head")

            # 3) Grant privileges on schema and tables to non-superuser role
            test_role = "aelus_test"
            # Schema usage
            conn.execute(text('GRANT USAGE ON SCHEMA public TO "' + test_role + '"'))
            # Table DML privileges for existing tables
            conn.execute(
                text(
                    'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "'
                    + test_role
                    + '"'
                )
            )
            # Future tables default privileges
            conn.execute(
                text(
                    'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "'
                    + test_role
                    + '"'
                )
            )
            # Sequences (if any) for future-proofing
            conn.execute(
                text(
                    'GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO "'
                    + test_role
                    + '"'
                )
            )
    finally:
        test_sync_engine.dispose()

    # Build async engine DSN for the non-superuser role
    from sqlalchemy.engine import make_url as _make_url

    app_test_url = _make_url(test_db_url).set(username="aelus_test", password="aelus_test_password")
    app_test_url_async = str(app_test_url).replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(
        app_test_url_async,
        poolclass=NullPool,
        echo=False,
    )

    yield engine

    # Cleanup: drop test database
    try:
        engine.sync_engine.dispose()

        # Build URL directly from individual config values
        base_url = (
            f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )
        admin_url = get_postgres_admin_url(base_url)
        sync_engine = create_engine(
            admin_url,
            isolation_level="AUTOCOMMIT",
            poolclass=NullPool,
        )

        with sync_engine.connect() as conn:
            # Terminate existing connections
            conn.execute(
                text("""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = :db_name
                    AND pid <> pg_backend_pid()
                """),
                {"db_name": test_db_name},
            )
            # Validate database name format before using in DDL
            if not test_db_name.replace("_", "").replace("-", "").isalnum():
                raise ValueError(f"Invalid test database name format: {test_db_name}")
            conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
    except Exception as e:
        # Log but don't fail on cleanup errors
        print(f"Warning: Failed to cleanup test database: {e}")
    finally:
        if "sync_engine" in locals():
            sync_engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_db_setup(test_db_engine):
    """
    Set up test database schema (session-scoped).

    Migrations and extension creation are already handled in test_db_engine
    using admin privileges to avoid RLS bypass. This fixture is kept for
    backward compatibility and potential future setup steps.
    """
    yield


@pytest_asyncio.fixture
async def db_session(test_db_engine, test_db_setup) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a transactional database session for each test.

    Each test gets a fresh session with automatic rollback after the test.
    This ensures test isolation.

    Uses nested transaction (savepoint) to allow endpoints to call commit()
    while still rolling back all changes at the end of the test.
    """
    # Create session factory
    async_session_factory = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        # Automatically restart a SAVEPOINT after a nested transaction ends (commit/rollback)
        # This keeps the session usable even if a statement inside tests aborts the savepoint
        # (e.g., RLS violations), preventing teardown errors when releasing the savepoint.
        try:
            from sqlalchemy import event
            from sqlalchemy.exc import InvalidRequestError

            @event.listens_for(session.sync_session, "after_transaction_end")
            def _restart_savepoint(sess, trans):  # type: ignore[no-redef]
                if trans.nested and not getattr(trans._parent, "nested", False):
                    try:
                        sess.begin_nested()
                    except InvalidRequestError:
                        # When the transaction context manager is finalizing,
                        # emitting new commands can raise InvalidRequestError.
                        # It's safe to skip re-establishing the savepoint here
                        # because the outer transaction rollback will clean up.
                        pass
        except Exception:
            pass
        # Start an outer transaction
        async with session.begin():
            # Create a nested transaction (savepoint)
            # This allows the endpoint to call commit() on the nested transaction
            # while the outer transaction will still rollback everything
            nested = await session.begin_nested()
            try:
                yield session
            finally:
                # Ensure nested savepoint is cleaned up even if it is in failed state
                try:
                    if getattr(nested, "is_active", False):
                        await nested.rollback()
                except Exception:
                    pass
                # Rollback outer transaction to clean up all changes
                try:
                    await session.rollback()
                except Exception:
                    pass


@pytest.fixture
def override_get_db(db_session: AsyncSession):
    """
    Override the get_db dependency to use test database.

    This ensures all API endpoints use the test database session.

    Args:
        db_session: Test database session

    Returns:
        Async generator function that yields the test database session
    """

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        # Ensure tenant context is set for RLS when using overridden DB in API tests
        try:
            from app.core.database import set_tenant_context as _set_tenant_ctx
            from app.core.logging import _tenant_id

            tenant_id = _tenant_id.get()
            if tenant_id:
                await _set_tenant_ctx(db_session, str(tenant_id))
        except Exception:
            # In tests without auth context, proceed; RLS will block as per policies
            pass
        yield db_session

    return _override_get_db


@pytest.fixture
def override_get_admin_db(db_session: AsyncSession):
    """
    Override the get_admin_db dependency to use test database.

    Admin operations don't set tenant context, so they can operate
    on the tenants table directly (per RLS policies).

    Args:
        db_session: Test database session

    Returns:
        Async generator function that yields the test database session
    """

    async def _override_get_admin_db() -> AsyncGenerator[AsyncSession, None]:
        # Admin operations work without tenant context
        yield db_session

    return _override_get_admin_db


# ============================================================================
# Redis Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def redis_client() -> AsyncGenerator[Redis, None]:
    """
    Provide a Redis client for testing.

    Uses a separate Redis database (15) for tests to avoid conflicts.
    Automatically flushes the test database before and after each test.
    """
    # Create Redis client for test database (DB 15)
    client = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=15,  # Dedicated test database
        decode_responses=True,
    )

    # Flush test database before test
    await client.flushdb()

    yield client

    # Flush test database after test
    await client.flushdb()
    await client.aclose()


@pytest_asyncio.fixture
async def redis_cache_client() -> AsyncGenerator[Redis, None]:
    """
    Provide a Redis client for cache testing.

    Separate from main Redis client for cache-specific tests.
    """
    client = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=14,  # Dedicated cache test database
        decode_responses=True,
    )

    await client.flushdb()

    yield client

    await client.flushdb()
    await client.aclose()


# ============================================================================
# FastAPI TestClient Fixtures
# ============================================================================


@pytest.fixture
def client(override_get_db, override_get_admin_db) -> Generator[TestClient, None, None]:
    """
    Provide a FastAPI TestClient for API testing.

    Automatically uses the test database via dependency override.
    """
    from app.core.database import get_admin_db

    # Override database dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_admin_db] = override_get_admin_db

    with TestClient(app) as test_client:
        yield test_client

    # Clear overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(override_get_db, override_get_admin_db) -> AsyncGenerator:
    """
    Provide an async HTTP client for testing.

    Use this for testing async endpoints.
    Dependency overrides are cleared after test execution to prevent pollution.
    """
    from httpx import ASGITransport, AsyncClient

    from app.core.database import get_admin_db

    # Set up dependency overrides before test
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_admin_db] = override_get_admin_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    finally:
        # Always clear overrides after test, even if test fails
        app.dependency_overrides.clear()


# ============================================================================
# Factory Fixtures
# ============================================================================


@pytest.fixture
def factories(db_session):
    """
    Provide access to all test factories with session pre-configured.

    Returns a wrapper object that automatically passes the db_session
    to all factory functions.
    """
    from tests import factories as test_factories

    class FactoriesWrapper:
        """Wrapper to automatically pass session to factory functions."""

        def __init__(self, session):
            self.session = session

        async def create_tenant(self, **kwargs):
            return await test_factories.create_tenant_async(self.session, **kwargs)

        async def create_user(self, tenant=None, **kwargs):
            return await test_factories.create_user_async(self.session, tenant, **kwargs)

        async def create_repository(self, tenant=None, **kwargs):
            return await test_factories.create_repository_async(self.session, tenant, **kwargs)

        async def create_code_node(self, tenant=None, repository=None, **kwargs):
            return await test_factories.create_code_node_async(
                self.session, tenant, repository, **kwargs
            )

        async def create_code_edge(self, tenant=None, source_node=None, target_node=None, **kwargs):
            return await test_factories.create_code_edge_async(
                self.session, tenant, source_node, target_node, **kwargs
            )

        async def create_embedding(self, tenant=None, node=None, **kwargs):
            return await test_factories.create_embedding_async(self.session, tenant, node, **kwargs)

        async def create_tenant_with_users(self, user_count=3, **tenant_kwargs):
            return await test_factories.create_tenant_with_users(
                self.session, user_count, **tenant_kwargs
            )

        async def create_repository_with_nodes(self, node_count=10, tenant=None, **repo_kwargs):
            return await test_factories.create_repository_with_nodes(
                self.session, node_count, tenant, **repo_kwargs
            )

        async def create_complete_code_graph(self, node_count=10, edge_count=15, tenant=None):
            return await test_factories.create_complete_code_graph(
                self.session, node_count, edge_count, tenant
            )

    return FactoriesWrapper(db_session)


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def sample_tenant_data():
    """Provide sample tenant data for testing."""
    return {
        "name": "Test Tenant",
        "settings": {
            "max_repositories": 10,
            "max_users": 5,
        },
    }


@pytest.fixture
def sample_repository_data():
    """Provide sample repository data for testing."""
    return {
        "name": "test-repo",
        "url": "https://github.com/test/repo",
        "branch": "main",
        "language": "python",
    }


@pytest.fixture
def sample_user_data():
    """Provide sample user data for testing."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
    }


# ============================================================================
# Cleanup Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """
    Automatically clean up after each test.

    This fixture runs after every test to ensure clean state.
    """
    yield
    # Cleanup logic runs here after test completes
    # Database cleanup is handled by db_session rollback
    # Redis cleanup is handled by redis_client fixture


# ============================================================================
# Performance Fixtures
# ============================================================================


@pytest.fixture
def benchmark_timer():
    """
    Provide a simple timer for performance testing.

    Usage:
        with benchmark_timer() as timer:
            # code to benchmark
        assert timer.elapsed < 1.0  # Assert took less than 1 second
    """
    import time
    from contextlib import contextmanager

    @contextmanager
    def timer():
        class Timer:
            def __init__(self):
                self.start = time.time()
                self.elapsed = 0

        t = Timer()
        yield t
        t.elapsed = time.time() - t.start

    return timer
