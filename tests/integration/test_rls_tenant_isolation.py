"""Integration tests for Row-Level Security (RLS) tenant isolation.

Tests verify that:
1. RLS policies prevent cross-tenant data access
2. Tenants can only see their own data
3. INSERT/UPDATE/DELETE operations respect tenant boundaries
4. Performance impact of RLS is acceptable
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import set_tenant_context
from app.models.code_graph import CodeNode
from app.utils.jwt import create_access_token
from tests.factories import create_repository_async, create_tenant_async


@pytest.mark.asyncio
class TestRLSTenantIsolation:
    """Test RLS policies enforce tenant isolation."""

    async def test_select_isolation_code_nodes(self, db_session: AsyncSession) -> None:
        """Test that SELECT queries only return data for current tenant."""
        # Create two tenants
        tenant1 = await create_tenant_async(db_session, name="Tenant 1")
        tenant2 = await create_tenant_async(db_session, name="Tenant 2")
        await db_session.flush()

        # Create repositories for each tenant
        repo1 = await create_repository_async(db_session, tenant_id=tenant1.id, name="repo1")
        repo2 = await create_repository_async(db_session, tenant_id=tenant2.id, name="repo2")
        await db_session.flush()

        # Create code nodes for each tenant
        node1 = CodeNode(
            id=uuid4(),
            tenant_id=tenant1.id,
            repo_id=repo1.id,
            node_type="function",
            qualified_name="tenant1.function1",
            name="function1",
            file_path="/test1.py",
        )
        node2 = CodeNode(
            id=uuid4(),
            tenant_id=tenant2.id,
            repo_id=repo2.id,
            node_type="function",
            qualified_name="tenant2.function2",
            name="function2",
            file_path="/test2.py",
        )
        db_session.add(node1)
        db_session.add(node2)
        await db_session.commit()

        # Set tenant context to tenant1
        await set_tenant_context(db_session, str(tenant1.id))

        # Query should only return tenant1's nodes
        result = await db_session.execute(text("SELECT * FROM code_nodes"))
        rows = result.fetchall()

        assert len(rows) == 1
        assert str(rows[0].tenant_id) == str(tenant1.id)
        assert rows[0].qualified_name == "tenant1.function1"

        # Switch to tenant2
        await db_session.commit()
        await set_tenant_context(db_session, str(tenant2.id))

        # Query should only return tenant2's nodes
        result = await db_session.execute(text("SELECT * FROM code_nodes"))
        rows = result.fetchall()

        assert len(rows) == 1
        assert str(rows[0].tenant_id) == str(tenant2.id)
        assert rows[0].qualified_name == "tenant2.function2"

    async def test_insert_isolation(self, db_session: AsyncSession) -> None:
        """Test that INSERT operations enforce tenant_id matching."""
        tenant1 = await create_tenant_async(db_session, name="Tenant 1")
        tenant2 = await create_tenant_async(db_session, name="Tenant 2")
        await db_session.flush()

        repo1 = await create_repository_async(db_session, tenant_id=tenant1.id, name="repo1")
        await db_session.flush()

        # Set tenant context to tenant1
        await set_tenant_context(db_session, str(tenant1.id))

        # Try to insert a node with tenant2's ID (should fail RLS policy)
        # RLS will raise a database error when trying to insert with wrong tenant_id
        from sqlalchemy.exc import DBAPIError, IntegrityError

        with pytest.raises((DBAPIError, IntegrityError)):
            await db_session.execute(
                text("""
                    INSERT INTO code_nodes (id, tenant_id, repo_id, node_type, qualified_name, name, file_path, metadata, created_at, updated_at)
                    VALUES (:id, :tenant_id, :repo_id, 'function', 'test.func', 'func', '/test.py', '{}', NOW(), NOW())
                """),
                {
                    "id": str(uuid4()),
                    "tenant_id": str(tenant2.id),  # Wrong tenant!
                    "repo_id": str(repo1.id),
                },
            )
            await db_session.commit()

    async def test_update_isolation(self, db_session: AsyncSession) -> None:
        """Test that UPDATE operations only affect current tenant's data."""
        tenant1 = await create_tenant_async(db_session, name="Tenant 1")
        tenant2 = await create_tenant_async(db_session, name="Tenant 2")
        await db_session.flush()

        repo1 = await create_repository_async(db_session, tenant_id=tenant1.id, name="repo1")
        repo2 = await create_repository_async(db_session, tenant_id=tenant2.id, name="repo2")
        await db_session.flush()

        # Create nodes for both tenants
        node1_id = uuid4()
        node2_id = uuid4()

        await db_session.execute(
            text("""
                INSERT INTO code_nodes (id, tenant_id, repo_id, node_type, qualified_name, name, file_path, metadata, created_at, updated_at)
                VALUES
                (:id1, :tenant1, :repo1, 'function', 'func1', 'func1', '/test1.py', '{}', NOW(), NOW()),
                (:id2, :tenant2, :repo2, 'function', 'func2', 'func2', '/test2.py', '{}', NOW(), NOW())
            """),
            {
                "id1": str(node1_id),
                "tenant1": str(tenant1.id),
                "repo1": str(repo1.id),
                "id2": str(node2_id),
                "tenant2": str(tenant2.id),
                "repo2": str(repo2.id),
            },
        )
        await db_session.commit()

        # Set tenant context to tenant1
        await set_tenant_context(db_session, str(tenant1.id))

        # Try to update tenant2's node (should not update due to RLS)
        result = await db_session.execute(
            text("UPDATE code_nodes SET name = 'updated' WHERE id = :id"),
            {"id": str(node2_id)},
        )

        # Verify no rows were updated
        assert result.rowcount == 0

        # Update tenant1's node (should succeed)
        result = await db_session.execute(
            text("UPDATE code_nodes SET name = 'updated' WHERE id = :id"),
            {"id": str(node1_id)},
        )
        await db_session.commit()

        assert result.rowcount == 1

    async def test_delete_isolation(self, db_session: AsyncSession) -> None:
        """Test that DELETE operations only affect current tenant's data."""
        tenant1 = await create_tenant_async(db_session, name="Tenant 1")
        tenant2 = await create_tenant_async(db_session, name="Tenant 2")
        await db_session.flush()

        repo1 = await create_repository_async(db_session, tenant_id=tenant1.id, name="repo1")
        repo2 = await create_repository_async(db_session, tenant_id=tenant2.id, name="repo2")
        await db_session.flush()

        # Create nodes for both tenants
        node1_id = uuid4()
        node2_id = uuid4()

        await db_session.execute(
            text("""
                INSERT INTO code_nodes (id, tenant_id, repo_id, node_type, qualified_name, name, file_path, metadata, created_at, updated_at)
                VALUES
                (:id1, :tenant1, :repo1, 'function', 'func1', 'func1', '/test1.py', '{}', NOW(), NOW()),
                (:id2, :tenant2, :repo2, 'function', 'func2', 'func2', '/test2.py', '{}', NOW(), NOW())
            """),
            {
                "id1": str(node1_id),
                "tenant1": str(tenant1.id),
                "repo1": str(repo1.id),
                "id2": str(node2_id),
                "tenant2": str(tenant2.id),
                "repo2": str(repo2.id),
            },
        )
        await db_session.commit()

        # Set tenant context to tenant1
        await set_tenant_context(db_session, str(tenant1.id))

        # Try to delete tenant2's node (should not delete due to RLS)
        result = await db_session.execute(
            text("DELETE FROM code_nodes WHERE id = :id"),
            {"id": str(node2_id)},
        )

        # Verify no rows were deleted
        assert result.rowcount == 0

        # Delete tenant1's node (should succeed)
        result = await db_session.execute(
            text("DELETE FROM code_nodes WHERE id = :id"),
            {"id": str(node1_id)},
        )
        await db_session.commit()

        assert result.rowcount == 1

    async def test_cross_tenant_access_via_api(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that API endpoints respect RLS tenant isolation."""
        # Create two tenants with repositories
        tenant1 = await create_tenant_async(db_session, name="Tenant 1")
        tenant2 = await create_tenant_async(db_session, name="Tenant 2")
        await db_session.flush()

        await create_repository_async(
            db_session, tenant_id=tenant1.id, name="repo1", git_url="https://github.com/test/repo1"
        )
        await create_repository_async(
            db_session, tenant_id=tenant2.id, name="repo2", git_url="https://github.com/test/repo2"
        )
        await db_session.commit()

        # Create JWT token for tenant1
        token1 = create_access_token(tenant_id=tenant1.id)

        # Tenant1 should see their own repository
        response = await async_client.get(
            "/api/v1/repositories/",  # Add trailing slash to match route definition
            headers={
                "Authorization": f"Bearer {token1}",
                "X-Tenant-ID": str(tenant1.id),
            },
        )

        assert response.status_code == 200
        repos = response.json()
        assert len(repos) == 1
        assert repos[0]["name"] == "repo1"

        # Tenant1 should NOT see tenant2's repository
        # Even if they try to query with tenant2's ID in header (JWT validation prevents this)
        response = await async_client.get(
            "/api/v1/repositories/",  # Add trailing slash
            headers={
                "Authorization": f"Bearer {token1}",
                "X-Tenant-ID": str(tenant2.id),  # Mismatch!
            },
        )

        # Should get 403 due to tenant mismatch
        assert response.status_code == 403

    async def test_rls_all_tables(self, db_session: AsyncSession) -> None:
        """Test that RLS is enabled on all tenant-scoped tables."""
        # Check RLS is enabled
        result = await db_session.execute(
            text("""
                SELECT tablename, rowsecurity
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename IN ('users', 'repositories', 'code_nodes', 'code_edges', 'code_embeddings', 'tenants')
            """)
        )
        tables = {row.tablename: row.rowsecurity for row in result.fetchall()}

        # Verify RLS is enabled on all tables
        assert tables.get("users") is True
        assert tables.get("repositories") is True
        assert tables.get("code_nodes") is True
        assert tables.get("code_edges") is True
        assert tables.get("code_embeddings") is True
        assert tables.get("tenants") is True

    async def test_rls_policies_exist(self, db_session: AsyncSession) -> None:
        """Test that RLS policies are created for all operations."""
        # Check policies exist
        result = await db_session.execute(
            text("""
                SELECT tablename, policyname, cmd
                FROM pg_policies
                WHERE schemaname = 'public'
                ORDER BY tablename, cmd
            """)
        )
        policies = result.fetchall()

        # Should have policies for SELECT, INSERT, UPDATE, DELETE on each table
        policy_names = {(row.tablename, row.cmd) for row in policies}

        # Check code_nodes has all policies
        assert ("code_nodes", "SELECT") in policy_names
        assert ("code_nodes", "INSERT") in policy_names
        assert ("code_nodes", "UPDATE") in policy_names
        assert ("code_nodes", "DELETE") in policy_names

        # Verify we have policies (at least 20: 4 operations × 5 tables)
        assert len(policies) >= 20


@pytest.mark.asyncio
class TestRLSPerformance:
    """Test performance impact of RLS policies."""

    async def test_rls_select_performance(self, db_session: AsyncSession) -> None:
        """Test that RLS doesn't significantly impact SELECT performance."""
        import time

        tenant = await create_tenant_async(db_session, name="Perf Test")
        await db_session.flush()

        repo = await create_repository_async(db_session, tenant_id=tenant.id, name="perf_repo")
        await db_session.flush()

        # Create 100 nodes
        nodes = [
            CodeNode(
                id=uuid4(),
                tenant_id=tenant.id,
                repo_id=repo.id,
                node_type="function",
                qualified_name=f"test.func{i}",
                name=f"func{i}",
                file_path=f"/test{i}.py",
            )
            for i in range(100)
        ]
        db_session.add_all(nodes)
        await db_session.commit()

        # Set tenant context
        await set_tenant_context(db_session, str(tenant.id))

        # Measure query time
        start = time.time()
        result = await db_session.execute(text("SELECT * FROM code_nodes"))
        rows = result.fetchall()
        elapsed = time.time() - start

        # Verify all rows returned
        assert len(rows) == 100

        # Performance check: RLS should not add significant overhead
        # Environment-aware threshold: stricter in local dev, more lenient in CI
        import os

        # CI environments often have variable performance
        is_ci = os.getenv("CI", "false").lower() == "true"
        threshold = 0.5 if is_ci else 0.1  # 500ms for CI, 100ms for local

        assert elapsed < threshold, (
            f"Query took {elapsed:.3f}s, expected < {threshold}s "
            f"(CI={is_ci}). RLS may be adding excessive overhead."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
