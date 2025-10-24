"""Test database migrations.

This module tests that migrations can be applied and rolled back successfully.
"""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


@pytest.fixture
def alembic_config():
    """Create Alembic configuration."""
    config = Config("alembic.ini")
    return config


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


def test_tenant_cascade_delete(alembic_config):
    """Test that deleting a tenant cascades to related tables."""
    import uuid

    from sqlalchemy.orm import Session

    from app.models.repository import Repository
    from app.models.tenant import Tenant, User

    engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    session = Session(bind=engine)

    try:
        # Create a test tenant
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Test Tenant Cascade",
            api_key_hash="test_hash_cascade",
            quotas={"vectors": 1000, "qps": 10, "storage_gb": 10, "repos": 5},
            settings={},
        )
        session.add(tenant)
        session.flush()

        # Create related user
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email="cascade@test.com",
            password_hash="test_hash",
            role="admin",
        )
        session.add(user)

        # Create related repository
        repo = Repository(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name="test-repo-cascade",
            git_url="https://github.com/test/repo",
            branch="main",
        )
        session.add(repo)
        session.commit()

        user_id = user.id
        repo_id = repo.id

        # Delete tenant
        session.delete(tenant)
        session.commit()

        # Verify cascade delete worked
        assert session.get(User, user_id) is None, "User should be deleted"
        assert session.get(Repository, repo_id) is None, "Repository should be deleted"

    finally:
        session.rollback()
        session.close()
        engine.dispose()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
