import pytest

from app.core.redis import redis_manager
from app.utils.quota import quota_service


@pytest.mark.asyncio
async def test_quota_service_increment_and_usage(redis_client):
    # Point quota service cache client to test redis
    redis_manager._cache_client = redis_client  # type: ignore[attr-defined]

    tenant = "tenant-test"

    # Ensure clean state
    await redis_client.flushdb()

    usage = await quota_service.get_usage(tenant)
    assert usage["api_calls"] == 0
    assert usage["vector_count"] == 0
    assert usage["storage_bytes"] == 0

    # Increment counters
    v = await quota_service.increment(tenant, "vector_count", 5)
    b = await quota_service.increment(tenant, "storage_bytes", 1000)
    assert v == 5
    assert b == 1000

    usage = await quota_service.get_usage(tenant)
    assert usage["vector_count"] == 5
    assert usage["storage_bytes"] == 1000


@pytest.mark.asyncio
async def test_quota_service_check_and_increment(redis_client):
    redis_manager._cache_client = redis_client  # type: ignore[attr-defined]

    tenant = "tenant-check"
    await redis_client.flushdb()

    # Resource not used yet, limit 10
    allowed, val = await quota_service.check_and_increment(tenant, "vector_count", 7, 10)
    assert allowed is True
    assert val == 7

    # Next increment would exceed
    allowed, val = await quota_service.check_and_increment(tenant, "vector_count", 5, 10)
    assert allowed is False
    # Current remains 7
    usage = await quota_service.get_usage(tenant)
    assert usage["vector_count"] == 7


@pytest.mark.asyncio
async def test_quota_service_limits_cache(redis_client):
    redis_manager._cache_client = redis_client  # type: ignore[attr-defined]

    tenant = "tenant-limits"
    await redis_client.flushdb()

    await quota_service.set_limits(
        tenant, {"qps": 3, "vectors": 100, "storage_gb": 1}, ttl_seconds=60
    )
    limits = await quota_service.get_limits(tenant)
    assert limits["qps"] == 3
    qps = await quota_service.get_qps_limit(tenant, default_qps=50)
    assert qps == 3
