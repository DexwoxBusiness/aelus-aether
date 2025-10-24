"""Integration tests for tenant CRUD operations."""

import uuid

import pytest
from sqlalchemy import select

from app.models.code_graph import CodeNode
from app.models.repository import Repository
from app.models.tenant import Tenant, User
from app.utils.security import hash_api_key, hash_password

# db_session fixture is provided by conftest.py


class TestTenantCRUD:
    """Test tenant CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_tenant(self, db_session):
        """Test creating a tenant."""
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Test Tenant CRUD",
            api_key_hash=hash_api_key("aelus_test123456789012345678901234"),
            quotas={"vectors": 500000, "qps": 50, "storage_gb": 100, "repos": 10},
            settings={"feature_flags": {"new_ui": True}},
            is_active=True,
        )

        db_session.add(tenant)
        await db_session.flush()

        # Verify tenant was created
        result = await db_session.execute(select(Tenant).where(Tenant.id == tenant.id))
        saved_tenant = result.scalar_one()

        assert saved_tenant.name == "Test Tenant CRUD"
        assert saved_tenant.quotas["vectors"] == 500000
        assert saved_tenant.quotas["storage_gb"] == 100
        assert saved_tenant.settings["feature_flags"]["new_ui"] is True
        assert saved_tenant.is_active is True

    @pytest.mark.asyncio
    async def test_read_tenant(self, db_session):
        """Test reading a tenant."""
        # Create tenant
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Read Test Tenant",
            api_key_hash=hash_api_key("aelus_read12345678901234567890123"),
            quotas={"vectors": 100000, "qps": 20, "storage_gb": 50, "repos": 5},
            settings={},
        )
        db_session.add(tenant)
        await db_session.flush()

        # Read tenant
        result = await db_session.execute(select(Tenant).where(Tenant.name == "Read Test Tenant"))
        read_tenant = result.scalar_one()

        assert read_tenant.id == tenant.id
        assert read_tenant.quotas["repos"] == 5

    @pytest.mark.asyncio
    async def test_update_tenant(self, db_session):
        """Test updating a tenant."""
        # Create tenant
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Update Test Tenant",
            api_key_hash=hash_api_key("aelus_update123456789012345678901"),
            quotas={"vectors": 100000, "qps": 20, "storage_gb": 50, "repos": 5},
            settings={},
        )
        db_session.add(tenant)
        await db_session.flush()

        # Update tenant
        tenant.quotas["repos"] = 15
        tenant.settings = {"updated": True}
        await db_session.flush()

        # Verify update
        result = await db_session.execute(select(Tenant).where(Tenant.id == tenant.id))
        updated_tenant = result.scalar_one()

        assert updated_tenant.quotas["repos"] == 15
        assert updated_tenant.settings["updated"] is True

    @pytest.mark.asyncio
    async def test_delete_tenant(self, db_session):
        """Test deleting a tenant."""
        # Create tenant
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Delete Test Tenant",
            api_key_hash=hash_api_key("aelus_delete123456789012345678901"),
            quotas={},
            settings={},
        )
        db_session.add(tenant)
        await db_session.flush()

        tenant_id = tenant.id

        # Delete tenant
        await db_session.delete(tenant)
        await db_session.flush()

        # Verify deletion
        result = await db_session.execute(select(Tenant).where(Tenant.id == tenant_id))
        deleted_tenant = result.scalar_one_or_none()

        assert deleted_tenant is None


class TestTenantRelationships:
    """Test tenant relationships and cascade deletes."""

    @pytest.mark.asyncio
    async def test_tenant_user_relationship(self, db_session):
        """Test tenant-user relationship."""
        # Create tenant
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Relationship Test Tenant",
            api_key_hash=hash_api_key("aelus_rel1234567890123456789012345"),
            quotas={},
            settings={},
        )
        db_session.add(tenant)
        await db_session.flush()

        # Create users
        user1 = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email="user1@relationship.test",
            password_hash=hash_password("password123"),
            role="admin",
        )
        user2 = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email="user2@relationship.test",
            password_hash=hash_password("password456"),
            role="member",
        )
        db_session.add_all([user1, user2])
        await db_session.flush()

        # Verify relationship
        await db_session.refresh(tenant)

        assert len(tenant.users) == 2
        assert any(u.email == "user1@relationship.test" for u in tenant.users)

    @pytest.mark.asyncio
    async def test_cascade_delete_users(self, db_session):
        """Test that deleting tenant cascades to users."""
        # Create tenant with user
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Cascade User Test",
            api_key_hash=hash_api_key("aelus_cascade12345678901234567890"),
            quotas={},
            settings={},
        )
        db_session.add(tenant)
        await db_session.flush()

        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email="cascade@test.com",
            password_hash=hash_password("password"),
            role="member",
        )
        db_session.add(user)
        await db_session.flush()

        user_id = user.id

        # Delete tenant
        await db_session.delete(tenant)
        await db_session.flush()

        # Verify user was deleted
        result = await db_session.execute(select(User).where(User.id == user_id))
        deleted_user = result.scalar_one_or_none()

        assert deleted_user is None, "User should be cascade deleted"

    @pytest.mark.asyncio
    async def test_cascade_delete_repositories(self, db_session):
        """Test that deleting tenant cascades to repositories."""
        # Create tenant with repository
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Cascade Repo Test",
            api_key_hash=hash_api_key("aelus_cascrepo1234567890123456789"),
            quotas={},
            settings={},
        )
        db_session.add(tenant)
        await db_session.flush()

        repo = Repository(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name="cascade-repo",
            git_url="https://github.com/test/cascade",
            branch="main",
        )
        db_session.add(repo)
        await db_session.flush()

        repo_id = repo.id

        # Delete tenant
        await db_session.delete(tenant)
        await db_session.flush()

        # Verify repository was deleted
        result = await db_session.execute(select(Repository).where(Repository.id == repo_id))
        deleted_repo = result.scalar_one_or_none()

        assert deleted_repo is None, "Repository should be cascade deleted"

    @pytest.mark.asyncio
    async def test_cascade_delete_code_graph(self, db_session):
        """Test that deleting tenant cascades to code graph entities."""
        # Create tenant and repository
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Cascade Graph Test",
            api_key_hash=hash_api_key("aelus_cascgraph123456789012345678"),
            quotas={},
            settings={},
        )
        db_session.add(tenant)
        await db_session.flush()

        repo = Repository(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name="graph-repo",
            git_url="https://github.com/test/graph",
            branch="main",
        )
        db_session.add(repo)
        await db_session.flush()

        # Create code node
        node = CodeNode(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            repo_id=repo.id,
            node_type="Function",
            qualified_name="test.module.function",
            name="function",
            file_path="/test/module.py",
            source_code="def function(): pass",
        )
        db_session.add(node)
        await db_session.flush()

        node_id = node.id

        # Delete tenant
        await db_session.delete(tenant)
        await db_session.flush()

        # Verify code node was deleted
        result = await db_session.execute(select(CodeNode).where(CodeNode.id == node_id))
        deleted_node = result.scalar_one_or_none()

        assert deleted_node is None, "Code node should be cascade deleted"


class TestMultiTenantIsolation:
    """Test multi-tenant data isolation."""

    @pytest.mark.asyncio
    async def test_tenant_data_isolation(self, db_session):
        """Test that tenants cannot see each other's data."""
        # Create two tenants
        tenant1 = Tenant(
            id=uuid.uuid4(),
            name="Tenant 1",
            api_key_hash=hash_api_key("aelus_tenant1234567890123456789012"),
            quotas={},
            settings={},
        )
        tenant2 = Tenant(
            id=uuid.uuid4(),
            name="Tenant 2",
            api_key_hash=hash_api_key("aelus_tenant2234567890123456789012"),
            quotas={},
            settings={},
        )
        db_session.add_all([tenant1, tenant2])
        await db_session.flush()

        # Create repositories for each tenant
        repo1 = Repository(
            id=uuid.uuid4(),
            tenant_id=tenant1.id,
            name="tenant1-repo",
            git_url="https://github.com/tenant1/repo",
            branch="main",
        )
        repo2 = Repository(
            id=uuid.uuid4(),
            tenant_id=tenant2.id,
            name="tenant2-repo",
            git_url="https://github.com/tenant2/repo",
            branch="main",
        )
        db_session.add_all([repo1, repo2])
        await db_session.flush()

        # Query repositories for tenant1
        result = await db_session.execute(
            select(Repository).where(Repository.tenant_id == tenant1.id)
        )
        tenant1_repos = list(result.scalars().all())

        # Verify isolation
        assert len(tenant1_repos) == 1
        assert tenant1_repos[0].name == "tenant1-repo"
        assert all(r.tenant_id == tenant1.id for r in tenant1_repos)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
