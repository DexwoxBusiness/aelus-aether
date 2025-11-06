"""Integration tests for AAET-29 Tenant Management Admin Endpoints.

Covers:
- GET /admin/tenants (pagination)
- GET /admin/tenants/{tenant_id} (includes usage)
- PATCH /admin/tenants/{tenant_id}/quotas
- DELETE /admin/tenants/{tenant_id} (soft delete)
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.redis import redis_manager
from app.utils.quota import quota_service
from tests.factories import create_tenant_async


@pytest.mark.asyncio
@pytest.mark.integration
class TestAdminTenantManagement:
    async def test_list_tenants_pagination(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Ensure at least 3 tenants exist
        for _ in range(3):
            await create_tenant_async(db_session)
        await db_session.flush()

        settings.admin_api_key = "test-admin-key-12345"
        headers = {"X-Admin-Key": settings.admin_api_key}

        resp = await async_client.get(
            f"{settings.api_prefix}/admin/tenants",
            params={"page": 1, "page_size": 2},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data and isinstance(data["items"], list)
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total"] >= len(data["items"]) >= 0

    async def test_get_tenant_detail_includes_usage(
        self, async_client: AsyncClient, db_session: AsyncSession, redis_client
    ) -> None:
        # Route uses Redis for usage; ensure isolated client is set
        redis_manager._cache_client = redis_client
        await redis_client.flushdb()

        tenant = await create_tenant_async(db_session)
        await db_session.flush()

        # Set some usage
        await quota_service.increment(str(tenant.id), "api_calls", 3)
        await quota_service.increment(str(tenant.id), "vector_count", 7)
        await quota_service.increment(str(tenant.id), "storage_bytes", 1024)

        settings.admin_api_key = "test-admin-key-12345"
        headers = {"X-Admin-Key": settings.admin_api_key}

        resp = await async_client.get(
            f"{settings.api_prefix}/admin/tenants/{tenant.id}",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(tenant.id)
        assert "usage" in data
        assert data["usage"]["api_calls"] == 3
        assert data["usage"]["vector_count"] == 7
        assert data["usage"]["storage_bytes"] == 1024

    async def test_patch_tenant_quotas_updates_and_caches(
        self, async_client: AsyncClient, db_session: AsyncSession, redis_client
    ) -> None:
        redis_manager._cache_client = redis_client
        await redis_client.flushdb()

        tenant = await create_tenant_async(db_session)
        await db_session.flush()

        settings.admin_api_key = "test-admin-key-12345"
        headers = {"X-Admin-Key": settings.admin_api_key}

        resp = await async_client.patch(
            f"{settings.api_prefix}/admin/tenants/{tenant.id}/quotas",
            json={"quotas": {"qps": 123, "vectors": 999999}},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["quotas"]["qps"] == 123
        assert data["quotas"]["vectors"] == 999999

        # Cached limits should reflect updates
        cached = await quota_service.get_limits(str(tenant.id))
        assert cached.get("qps") == 123
        assert cached.get("vectors") == 999999

    async def test_soft_delete_tenant_and_404_after(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        tenant = await create_tenant_async(db_session)
        await db_session.flush()

        settings.admin_api_key = "test-admin-key-12345"
        headers = {"X-Admin-Key": settings.admin_api_key}

        # Soft delete
        resp = await async_client.delete(
            f"{settings.api_prefix}/admin/tenants/{tenant.id}",
            headers=headers,
        )
        assert resp.status_code == 204

        # Fetch should 404
        resp2 = await async_client.get(
            f"{settings.api_prefix}/admin/tenants/{tenant.id}",
            headers=headers,
        )
        assert resp2.status_code == 404
