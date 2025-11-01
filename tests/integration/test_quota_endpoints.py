"""Integration tests for quota admin endpoints (AAET-25)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.redis import redis_manager
from app.utils.jwt import create_access_token
from app.utils.quota import quota_service
from tests.factories import create_tenant_async


@pytest.mark.asyncio
@pytest.mark.integration
class TestQuotaEndpointsGetQuota:
    """Test GET /{tenant_id}/quota endpoint."""

    async def test_get_quota_success(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test retrieving tenant quotas."""
        # Create tenant with specific quotas
        tenant = await create_tenant_async(
            db_session,
            quotas={"vectors": 100000, "qps": 25, "storage_gb": 50, "repos": 5},
        )
        await db_session.flush()

        token = create_access_token(tenant_id=tenant.id)

        response = await async_client.get(
            f"{settings.api_prefix}/tenants/{tenant.id}/quota",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant.id),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == str(tenant.id)
        assert "quotas" in data
        assert data["quotas"]["vectors"] == 100000
        assert data["quotas"]["qps"] == 25
        assert data["quotas"]["storage_gb"] == 50
        assert data["quotas"]["repos"] == 5

    async def test_get_quota_not_found(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test getting quota for non-existent tenant."""
        tenant = await create_tenant_async(db_session)
        await db_session.flush()

        token = create_access_token(tenant_id=tenant.id)

        # Use a fake UUID
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await async_client.get(
            f"{settings.api_prefix}/tenants/{fake_id}/quota",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant.id),
            },
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_quota_requires_authentication(self, async_client: AsyncClient):
        """Test that quota endpoint requires authentication."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await async_client.get(f"{settings.api_prefix}/tenants/{fake_id}/quota")

        assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.integration
class TestQuotaEndpointsUpdateQuota:
    """Test PUT /{tenant_id}/quota endpoint."""

    async def test_update_quota_success(
        self, async_client: AsyncClient, db_session: AsyncSession, redis_client
    ):
        """Test updating tenant quotas."""
        redis_manager._cache_client = redis_client
        await redis_client.flushdb()

        tenant = await create_tenant_async(
            db_session,
            quotas={"vectors": 500000, "qps": 50, "storage_gb": 100, "repos": 10},
        )
        await db_session.flush()

        token = create_access_token(tenant_id=tenant.id)

        # Update quotas
        new_quotas = {"vectors": 1000000, "qps": 100, "storage_gb": 200}

        response = await async_client.put(
            f"{settings.api_prefix}/tenants/{tenant.id}/quota",
            json=new_quotas,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant.id),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == str(tenant.id)
        assert data["quotas"]["vectors"] == 1000000
        assert data["quotas"]["qps"] == 100
        assert data["quotas"]["storage_gb"] == 200

        # Verify Redis cache was updated
        cached_limits = await quota_service.get_limits(str(tenant.id))
        assert cached_limits["vectors"] == 1000000
        assert cached_limits["qps"] == 100
        assert cached_limits["storage_gb"] == 200

    async def test_update_quota_partial_update(
        self, async_client: AsyncClient, db_session: AsyncSession, redis_client
    ):
        """Test partial quota update (only some fields)."""
        redis_manager._cache_client = redis_client
        await redis_client.flushdb()

        tenant = await create_tenant_async(
            db_session,
            quotas={"vectors": 500000, "qps": 50, "storage_gb": 100, "repos": 10},
        )
        await db_session.flush()

        token = create_access_token(tenant_id=tenant.id)

        # Update only QPS
        response = await async_client.put(
            f"{settings.api_prefix}/tenants/{tenant.id}/quota",
            json={"qps": 75},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant.id),
            },
        )

        assert response.status_code == 200
        data = response.json()
        # QPS should be updated
        assert data["quotas"]["qps"] == 75
        # Other quotas should remain unchanged
        assert data["quotas"]["vectors"] == 500000
        assert data["quotas"]["storage_gb"] == 100

    async def test_update_quota_invalid_keys_ignored(
        self, async_client: AsyncClient, db_session: AsyncSession, redis_client
    ):
        """Test that invalid quota keys are ignored."""
        redis_manager._cache_client = redis_client
        await redis_client.flushdb()

        tenant = await create_tenant_async(db_session)
        await db_session.flush()

        token = create_access_token(tenant_id=tenant.id)

        # Try to update with invalid keys
        response = await async_client.put(
            f"{settings.api_prefix}/tenants/{tenant.id}/quota",
            json={"invalid_key": 999, "another_invalid": 123},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant.id),
            },
        )

        # Should fail because no valid keys provided
        assert response.status_code == 400
        assert "no valid quota keys" in response.json()["detail"].lower()

    async def test_update_quota_mixed_valid_invalid_keys(
        self, async_client: AsyncClient, db_session: AsyncSession, redis_client
    ):
        """Test updating with mix of valid and invalid keys."""
        redis_manager._cache_client = redis_client
        await redis_client.flushdb()

        tenant = await create_tenant_async(db_session)
        await db_session.flush()

        token = create_access_token(tenant_id=tenant.id)

        # Mix of valid and invalid keys
        response = await async_client.put(
            f"{settings.api_prefix}/tenants/{tenant.id}/quota",
            json={"qps": 75, "invalid_key": 999},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant.id),
            },
        )

        # Should succeed, ignoring invalid keys
        assert response.status_code == 200
        data = response.json()
        assert data["quotas"]["qps"] == 75
        # Invalid key should not be in quotas
        assert "invalid_key" not in data["quotas"]

    async def test_update_quota_not_found(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test updating quota for non-existent tenant."""
        tenant = await create_tenant_async(db_session)
        await db_session.flush()

        token = create_access_token(tenant_id=tenant.id)

        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await async_client.put(
            f"{settings.api_prefix}/tenants/{fake_id}/quota",
            json={"qps": 100},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant.id),
            },
        )

        assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.integration
class TestQuotaEndpointsGetUsage:
    """Test GET /{tenant_id}/usage endpoint."""

    async def test_get_usage_success(
        self, async_client: AsyncClient, db_session: AsyncSession, redis_client
    ):
        """Test retrieving tenant usage from Redis."""
        redis_manager._cache_client = redis_client
        await redis_client.flushdb()

        tenant = await create_tenant_async(db_session)
        await db_session.flush()

        # Set some usage in Redis
        await quota_service.increment(str(tenant.id), "api_calls", 100)
        await quota_service.increment(str(tenant.id), "vector_count", 5000)
        await quota_service.increment(str(tenant.id), "storage_bytes", 1024000)

        token = create_access_token(tenant_id=tenant.id)

        response = await async_client.get(
            f"{settings.api_prefix}/tenants/{tenant.id}/usage",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant.id),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == str(tenant.id)
        assert "usage" in data
        assert data["usage"]["api_calls"] == 100
        assert data["usage"]["vector_count"] == 5000
        assert data["usage"]["storage_bytes"] == 1024000

    async def test_get_usage_zero_when_no_usage(
        self, async_client: AsyncClient, db_session: AsyncSession, redis_client
    ):
        """Test that usage returns zeros for new tenant."""
        redis_manager._cache_client = redis_client
        await redis_client.flushdb()

        tenant = await create_tenant_async(db_session)
        await db_session.flush()

        token = create_access_token(tenant_id=tenant.id)

        response = await async_client.get(
            f"{settings.api_prefix}/tenants/{tenant.id}/usage",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant.id),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["usage"]["api_calls"] == 0
        assert data["usage"]["vector_count"] == 0
        assert data["usage"]["storage_bytes"] == 0

    async def test_get_usage_requires_authentication(self, async_client: AsyncClient):
        """Test that usage endpoint requires authentication."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await async_client.get(f"{settings.api_prefix}/tenants/{fake_id}/usage")

        assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.integration
class TestQuotaEndpointsIntegration:
    """Test quota endpoints working together."""

    async def test_quota_lifecycle(
        self, async_client: AsyncClient, db_session: AsyncSession, redis_client
    ):
        """Test complete quota lifecycle: create, update, use, check."""
        redis_manager._cache_client = redis_client
        redis_manager._rate_limit_client = redis_client
        await redis_client.flushdb()

        # 1. Create tenant with initial quotas
        tenant = await create_tenant_async(
            db_session,
            quotas={"vectors": 10000, "qps": 10, "storage_gb": 10, "repos": 5},
        )
        await db_session.flush()

        token = create_access_token(tenant_id=tenant.id)

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": str(tenant.id),
        }

        # 2. Get initial quotas
        response = await async_client.get(
            f"{settings.api_prefix}/tenants/{tenant.id}/quota",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["quotas"]["vectors"] == 10000

        # 3. Check initial usage (should be zero)
        response = await async_client.get(
            f"{settings.api_prefix}/tenants/{tenant.id}/usage",
            headers=headers,
        )
        assert response.status_code == 200
        initial_usage = response.json()["usage"]
        assert initial_usage["vector_count"] == 0

        # 4. Simulate some usage
        await quota_service.increment(str(tenant.id), "vector_count", 1000)
        await quota_service.increment(str(tenant.id), "storage_bytes", 4096000)

        # 5. Check updated usage
        response = await async_client.get(
            f"{settings.api_prefix}/tenants/{tenant.id}/usage",
            headers=headers,
        )
        assert response.status_code == 200
        usage = response.json()["usage"]
        assert usage["vector_count"] == 1000
        assert usage["storage_bytes"] == 4096000

        # 6. Update quotas
        response = await async_client.put(
            f"{settings.api_prefix}/tenants/{tenant.id}/quota",
            json={"vectors": 20000, "storage_gb": 20},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["quotas"]["vectors"] == 20000
        assert response.json()["quotas"]["storage_gb"] == 20

        # 7. Verify Redis cache was updated
        cached_limits = await quota_service.get_limits(str(tenant.id))
        assert cached_limits["vectors"] == 20000
        assert cached_limits["storage_gb"] == 20
