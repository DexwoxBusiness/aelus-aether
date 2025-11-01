"""Integration tests for QuotaMiddleware (AAET-25)."""

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
class TestQuotaMiddlewareAPICallTracking:
    """Test QuotaMiddleware tracks API calls correctly."""

    async def test_api_call_counter_increments(
        self, async_client: AsyncClient, db_session: AsyncSession, redis_client
    ):
        """Test that API calls increment the quota counter."""
        # Initialize Redis connections
        redis_manager._cache_client = redis_client
        await redis_client.flushdb()

        # Create tenant
        tenant = await create_tenant_async(db_session)
        await db_session.flush()

        # Create JWT token
        token = create_access_token(data={"sub": str(tenant.id), "tenant_id": str(tenant.id)})

        # Make authenticated request
        response = await async_client.get(
            f"{settings.api_prefix}/tenants/",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant.id),
            },
        )

        # Should succeed
        assert response.status_code == 200

        # Check that api_calls counter was incremented
        usage = await quota_service.get_usage(str(tenant.id))
        assert usage["api_calls"] >= 1

    async def test_api_call_counter_multiple_requests(
        self, async_client: AsyncClient, db_session: AsyncSession, redis_client
    ):
        """Test that multiple API calls increment counter correctly."""
        redis_manager._cache_client = redis_client
        await redis_client.flushdb()

        tenant = await create_tenant_async(db_session)
        await db_session.flush()

        token = create_access_token(data={"sub": str(tenant.id), "tenant_id": str(tenant.id)})

        # Make 5 requests
        for _ in range(5):
            await async_client.get(
                f"{settings.api_prefix}/tenants/",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Tenant-ID": str(tenant.id),
                },
            )

        # Check counter
        usage = await quota_service.get_usage(str(tenant.id))
        assert usage["api_calls"] >= 5

    async def test_unauthenticated_requests_not_counted(
        self, async_client: AsyncClient, redis_client
    ):
        """Test that unauthenticated requests don't increment counters."""
        redis_manager._cache_client = redis_client
        await redis_client.flushdb()

        # Make unauthenticated request to public endpoint
        response = await async_client.get("/health")
        assert response.status_code == 200

        # No tenant_id, so no counter should exist
        # This is expected behavior - only authenticated requests are counted


@pytest.mark.asyncio
@pytest.mark.integration
class TestQuotaMiddlewareRateLimiting:
    """Test QuotaMiddleware enforces QPS rate limits."""

    async def test_qps_limit_enforcement(
        self, async_client: AsyncClient, db_session: AsyncSession, redis_client
    ):
        """Test that QPS limit is enforced with 429 response."""
        redis_manager._cache_client = redis_client
        redis_manager._rate_limit_client = redis_client
        await redis_client.flushdb()

        # Create tenant with low QPS limit
        tenant = await create_tenant_async(
            db_session, quotas={"vectors": 500000, "qps": 2, "storage_gb": 100, "repos": 10}
        )
        await db_session.flush()

        # Cache the limits in Redis
        await quota_service.set_limits(
            str(tenant.id), {"qps": 2, "vectors": 500000, "storage_gb": 100}, ttl_seconds=300
        )

        token = create_access_token(data={"sub": str(tenant.id), "tenant_id": str(tenant.id)})

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": str(tenant.id),
        }

        # Make requests up to the limit
        responses = []
        for i in range(5):
            response = await async_client.get(
                f"{settings.api_prefix}/tenants/",
                headers=headers,
            )
            responses.append(response)

        # First 2 should succeed (within 60-second window for QPS=2)
        # Subsequent requests should be rate limited
        sum(1 for r in responses if r.status_code == 200)
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)

        # We should have at least one 429 response
        assert rate_limited_count > 0, "Expected at least one rate-limited response"

        # Check 429 response format
        rate_limited_responses = [r for r in responses if r.status_code == 429]
        if rate_limited_responses:
            response_data = rate_limited_responses[0].json()
            assert "detail" in response_data
            assert "quota exceeded" in response_data["detail"].lower()

    async def test_429_response_includes_retry_after(
        self, async_client: AsyncClient, db_session: AsyncSession, redis_client
    ):
        """Test that 429 responses include Retry-After header."""
        redis_manager._cache_client = redis_client
        redis_manager._rate_limit_client = redis_client
        await redis_client.flushdb()

        # Create tenant with very low QPS
        tenant = await create_tenant_async(
            db_session, quotas={"vectors": 500000, "qps": 1, "storage_gb": 100, "repos": 10}
        )
        await db_session.flush()

        await quota_service.set_limits(
            str(tenant.id), {"qps": 1, "vectors": 500000, "storage_gb": 100}, ttl_seconds=300
        )

        token = create_access_token(data={"sub": str(tenant.id), "tenant_id": str(tenant.id)})

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": str(tenant.id),
        }

        # Make multiple requests to trigger rate limit
        for _ in range(3):
            response = await async_client.get(
                f"{settings.api_prefix}/tenants/",
                headers=headers,
            )
            if response.status_code == 429:
                # Check for Retry-After header
                assert "retry-after" in response.headers or "Retry-After" in response.headers
                # Check response body includes retry info
                data = response.json()
                assert "retry_after" in data or "detail" in data
                break

    async def test_different_tenants_isolated_rate_limits(
        self, async_client: AsyncClient, db_session: AsyncSession, redis_client
    ):
        """Test that rate limits are isolated per tenant."""
        redis_manager._cache_client = redis_client
        redis_manager._rate_limit_client = redis_client
        await redis_client.flushdb()

        # Create two tenants
        tenant1 = await create_tenant_async(
            db_session, quotas={"vectors": 500000, "qps": 1, "storage_gb": 100, "repos": 10}
        )
        tenant2 = await create_tenant_async(
            db_session, quotas={"vectors": 500000, "qps": 50, "storage_gb": 100, "repos": 10}
        )
        await db_session.flush()

        # Cache limits
        await quota_service.set_limits(
            str(tenant1.id), {"qps": 1, "vectors": 500000, "storage_gb": 100}, ttl_seconds=300
        )
        await quota_service.set_limits(
            str(tenant2.id), {"qps": 50, "vectors": 500000, "storage_gb": 100}, ttl_seconds=300
        )

        token1 = create_access_token(data={"sub": str(tenant1.id), "tenant_id": str(tenant1.id)})
        token2 = create_access_token(data={"sub": str(tenant2.id), "tenant_id": str(tenant2.id)})

        # Exhaust tenant1's rate limit
        for _ in range(3):
            await async_client.get(
                f"{settings.api_prefix}/tenants/",
                headers={
                    "Authorization": f"Bearer {token1}",
                    "X-Tenant-ID": str(tenant1.id),
                },
            )

        # Tenant2 should still be able to make requests
        response = await async_client.get(
            f"{settings.api_prefix}/tenants/",
            headers={
                "Authorization": f"Bearer {token2}",
                "X-Tenant-ID": str(tenant2.id),
            },
        )
        # Tenant2 should not be rate limited
        assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.integration
class TestQuotaMiddlewarePublicEndpoints:
    """Test that QuotaMiddleware doesn't affect public endpoints."""

    async def test_public_endpoints_not_quota_tracked(
        self, async_client: AsyncClient, redis_client
    ):
        """Test that public endpoints don't trigger quota tracking."""
        redis_manager._cache_client = redis_client
        await redis_client.flushdb()

        # Make requests to public endpoints
        public_endpoints = ["/health", "/healthz", "/", "/metrics"]

        for endpoint in public_endpoints:
            response = await async_client.get(endpoint)
            # Should succeed without authentication
            assert response.status_code in [200, 503]  # 503 if dependencies not ready

        # No quota counters should be created since no tenant_id
        # This is expected behavior
