"""Pytest configuration and fixtures for Aelus-Aether tests.

This module provides centralized test fixtures for:
- Database sessions (with automatic cleanup)
- Redis clients (with automatic cleanup)
- FastAPI TestClient
- Test data factories
- Async support
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.core.database import Base, get_db
from app.main import app


# ============================================================================
# Test Database Configuration
# ============================================================================

# Test database URL (separate from production)
TEST_DATABASE_URL = settings.database_url.replace("/aelus_aether", "/aelus_aether_test")
TEST_DATABASE_URL_ASYNC = TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (require DB/Redis)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests (may take >5 seconds)"
    )
    config.addinivalue_line(
        "markers", "asyncio: Async tests"
    )


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
    test_db_name = f"aelus_aether_test_{test_run_id}"
    
    # Update test database URLs with unique name
    test_db_url = settings.database_url.replace("/aelus_aether", f"/{test_db_name}")
    test_db_url_async = test_db_url.replace("postgresql://", "postgresql+asyncpg://")
    
    # Create synchronous engine for database creation
    sync_engine = create_engine(
        settings.database_url.replace("/aelus_aether", "/postgres"),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    
    try:
        # Drop and recreate test database
        with sync_engine.connect() as conn:
            # Terminate existing connections to the test database
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{test_db_name}'
                AND pid <> pg_backend_pid()
            """))
            conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
            conn.execute(text(f"CREATE DATABASE {test_db_name}"))
    except Exception as e:
        sync_engine.dispose()
        raise RuntimeError(f"Failed to create test database: {e}") from e
    finally:
        sync_engine.dispose()
    
    # Create async engine for tests
    engine = create_async_engine(
        test_db_url_async,
        poolclass=NullPool,
        echo=False,
    )
    
    yield engine
    
    # Cleanup: drop test database
    try:
        engine.sync_engine.dispose()
        
        sync_engine = create_engine(
            settings.database_url.replace("/aelus_aether", "/postgres"),
            isolation_level="AUTOCOMMIT",
            poolclass=NullPool,
        )
        
        with sync_engine.connect() as conn:
            # Terminate existing connections
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{test_db_name}'
                AND pid <> pg_backend_pid()
            """))
            conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
    except Exception as e:
        # Log but don't fail on cleanup errors
        print(f"Warning: Failed to cleanup test database: {e}")
    finally:
        if 'sync_engine' in locals():
            sync_engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_db_setup(test_db_engine):
    """
    Set up test database schema (session-scoped).
    
    Creates all tables before tests and drops them after.
    """
    # Create all tables
    async with test_db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Drop all tables
    async with test_db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(test_db_engine, test_db_setup) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a transactional database session for each test.
    
    Each test gets a fresh session with automatic rollback after the test.
    This ensures test isolation.
    """
    # Create session factory
    async_session_factory = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_factory() as session:
        # Start a transaction
        async with session.begin():
            yield session
            # Rollback happens automatically when context exits


@pytest.fixture
def override_get_db(db_session):
    """
    Override the get_db dependency to use test database.
    
    This ensures all API endpoints use the test database session.
    """
    async def _override_get_db():
        yield db_session
    
    return _override_get_db


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
def client(override_get_db) -> Generator[TestClient, None, None]:
    """
    Provide a FastAPI TestClient for API testing.
    
    Automatically uses the test database via dependency override.
    """
    # Override database dependency
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture
def async_client(override_get_db):
    """
    Provide an async HTTP client for testing.
    
    Use this for testing async endpoints.
    """
    from httpx import AsyncClient
    
    app.dependency_overrides[get_db] = override_get_db
    
    async def _get_async_client():
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    return _get_async_client


# ============================================================================
# Factory Fixtures
# ============================================================================

@pytest.fixture
def factories(db_session):
    """
    Provide access to all test factories.
    
    Automatically configures factories to use the test database session.
    """
    from tests import factories as test_factories
    
    # Configure all factories to use test session
    test_factories.BaseFactory._meta.sqlalchemy_session = db_session
    
    return test_factories


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def sample_tenant_data():
    """Provide sample tenant data for testing."""
    return {
        "name": "Test Tenant",
        "slug": "test-tenant",
        "settings": {
            "max_repositories": 10,
            "max_users": 5,
        }
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
            
            def __enter__(self):
                return self
            
            def __exit__(self, *args):
                self.elapsed = time.time() - self.start
        
        t = Timer()
        yield t
    
    return timer
