"""Test database migrations.

This module tests that migrations can be applied and rolled back successfully.
"""

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


@pytest.fixture
def alembic_config():
    """Create Alembic configuration."""
    config = Config("alembic.ini")
    # Use DATABASE_URL from environment if available
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        config.set_main_option("sqlalchemy.url", db_url)
    return config


@pytest.mark.skipif(
    os.getenv("SKIP_MIGRATION_TESTS") == "true", reason="Migration tests skipped in CI"
)
def test_migration_upgrade_downgrade(alembic_config):
    """Test that migration 002 can upgrade and downgrade successfully."""
    # Upgrade to latest
    command.upgrade(alembic_config, "head")

    # Check that tables exist
    engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    inspector = inspect(engine)

    tables = inspector.get_table_names()

    # Verify all expected tables exist
    assert "tenants" in tables, "tenants table should exist"
    assert "users" in tables, "users table should exist"
    assert "repositories" in tables, "repositories table should exist"
    assert "code_nodes" in tables, "code_nodes table should exist"
    assert "code_edges" in tables, "code_edges table should exist"
    assert "code_embeddings" in tables, "code_embeddings table should exist"

    # Verify tenants table structure
    tenants_columns = {col["name"]: col for col in inspector.get_columns("tenants")}
    assert "id" in tenants_columns
    assert "name" in tenants_columns
    assert "api_key_hash" in tenants_columns
    assert "quotas" in tenants_columns
    assert "settings" in tenants_columns
    assert "is_active" in tenants_columns
    assert "created_at" in tenants_columns

    # Verify users table structure
    users_columns = {col["name"]: col for col in inspector.get_columns("users")}
    assert "id" in users_columns
    assert "tenant_id" in users_columns
    assert "email" in users_columns
    assert "password_hash" in users_columns
    assert "role" in users_columns

    # Verify foreign keys exist
    tenants_fks = inspector.get_foreign_keys("users")
    assert len(tenants_fks) > 0, "users table should have foreign key to tenants"

    # Downgrade to previous version
    command.downgrade(alembic_config, "001")

    # Verify old tables are back
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Old tables should exist, new tables should not
    assert "tenants" not in tables, "tenants table should not exist after downgrade"
    assert "users" not in tables, "users table should not exist after downgrade"
    assert "repositories" not in tables, "repositories table should not exist after downgrade"

    # Upgrade again to head for other tests
    command.upgrade(alembic_config, "head")

    engine.dispose()


@pytest.mark.skipif(
    os.getenv("SKIP_MIGRATION_TESTS") == "true", reason="Migration tests skipped in CI"
)
def test_tenant_cascade_delete(alembic_config):
    """Test that deleting a tenant cascades to related tables."""
    import uuid

    from app.utils.security import hash_api_key

    # Get database URL and convert to sync if needed
    url = alembic_config.get_main_option("sqlalchemy.url")
    if not url:
        pytest.skip("No database URL configured")

    # Replace asyncpg with psycopg2 for sync operations
    if "asyncpg" in url:
        url = url.replace("postgresql+asyncpg://", "postgresql://")

    engine = create_engine(url)

    with engine.connect() as conn:
        trans = conn.begin()

        # Create test tenant using raw SQL
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        repo_id = uuid.uuid4()

        conn.execute(
            text("""
            INSERT INTO tenants (id, name, api_key_hash, quotas, settings, is_active)
            VALUES (:id, :name, :api_key_hash, :quotas, :settings, :is_active)
        """),
            {
                "id": tenant_id,
                "name": "Test Tenant Cascade",
                "api_key_hash": hash_api_key("aelus_cascade_test1234567890123"),
                "quotas": '{"vectors": 1000, "qps": 10, "storage_gb": 10, "repos": 5}',
                "settings": "{}",
                "is_active": True,
            },
        )

        # Create related user
        conn.execute(
            text("""
            INSERT INTO users (id, tenant_id, email, password_hash, role, is_active)
            VALUES (:id, :tenant_id, :email, :password_hash, :role, :is_active)
        """),
            {
                "id": user_id,
                "tenant_id": tenant_id,
                "email": "cascade@test.com",
                "password_hash": "test_hash",
                "role": "admin",
                "is_active": True,
            },
        )

        # Create related repository
        conn.execute(
            text("""
            INSERT INTO repositories (id, tenant_id, name, git_url, branch)
            VALUES (:id, :tenant_id, :name, :git_url, :branch)
        """),
            {
                "id": repo_id,
                "tenant_id": tenant_id,
                "name": "test-repo-cascade",
                "git_url": "https://github.com/test/repo",
                "branch": "main",
            },
        )

        # Delete tenant
        conn.execute(text("DELETE FROM tenants WHERE id = :id"), {"id": tenant_id})

        # Verify cascade delete worked
        user_result = conn.execute(text("SELECT id FROM users WHERE id = :id"), {"id": user_id})
        assert user_result.fetchone() is None, "User should be cascade deleted"

        repo_result = conn.execute(
            text("SELECT id FROM repositories WHERE id = :id"), {"id": repo_id}
        )
        assert repo_result.fetchone() is None, "Repository should be cascade deleted"

        trans.rollback()

    engine.dispose()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
