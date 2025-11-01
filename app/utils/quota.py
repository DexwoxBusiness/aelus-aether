from __future__ import annotations

from typing import Any, cast

from app.core.logging import get_logger
from app.core.redis import redis_manager
from app.utils.tenant_context import make_tenant_key_safe

logger = get_logger(__name__)


class QuotaService:
    """Redis-backed per-tenant quota usage tracking.

    Tracks usage counters:
    - api_calls (monotonic)
    - vector_count (monotonic)
    - storage_bytes (monotonic)

    Quota limits are expected in Tenant.quotas and can be cached in Redis under
    key: tenant:{tenant_id}:quotas (JSON-serialized by caller).
    """

    @staticmethod
    async def get_usage(tenant_id: str) -> dict[str, int]:
        client = redis_manager.cache
        keys = {
            "api_calls": make_tenant_key_safe(tenant_id, "quota", "api_calls"),
            "vector_count": make_tenant_key_safe(tenant_id, "quota", "vector_count"),
            "storage_bytes": make_tenant_key_safe(tenant_id, "quota", "storage_bytes"),
        }
        pipe = client.pipeline()
        for k in keys.values():
            pipe.get(k)
        vals = await pipe.execute()

        def to_int(v: Any) -> int:
            try:
                return int(v) if v is not None else 0
            except Exception:
                return 0

        return {
            "api_calls": to_int(vals[0]),
            "vector_count": to_int(vals[1]),
            "storage_bytes": to_int(vals[2]),
        }

    @staticmethod
    async def increment(tenant_id: str, resource: str, amount: int) -> int:
        """Increment a usage counter and return new value."""
        client = redis_manager.cache
        key = make_tenant_key_safe(tenant_id, "quota", resource)
        new_val = await client.incrby(key, amount)
        return int(new_val)

    @staticmethod
    async def check_and_increment(
        tenant_id: str, resource: str, amount: int, limit: int
    ) -> tuple[bool, int]:
        """Atomically check limit and increment if within quota.

        Returns (allowed, new_value_or_current).
        """
        client = redis_manager.cache
        key = make_tenant_key_safe(tenant_id, "quota", resource)
        # Lua script for atomic check-and-increment
        script = (
            "local current = redis.call('GET', KEYS[1])\n"
            "if not current then current = 0 else current = tonumber(current) end\n"
            "local inc = tonumber(ARGV[1])\n"
            "local limit = tonumber(ARGV[2])\n"
            "local newv = current + inc\n"
            "if newv > limit then return {0, current} else redis.call('INCRBY', KEYS[1], inc); return {1, newv} end\n"
        )
        try:
            res = await client.eval(script, 1, key, amount, limit)  # type: ignore[no-untyped-call]
            seq = cast(list[Any], res)
            allowed = bool(int(seq[0]))
            value = int(seq[1])
            return allowed, value
        except Exception as e:
            logger.error(
                f"Quota check Lua script failed for tenant {tenant_id}, resource {resource}: {e}",
                extra={"tenant_id": tenant_id, "resource": resource},
            )
            # Fail closed for security - deny the operation
            return False, 0

    @staticmethod
    async def get_limits(tenant_id: str) -> dict[str, int]:
        client = redis_manager.cache
        key = make_tenant_key_safe(tenant_id, "quota", "limits")
        raw = await client.get(key)
        if not raw:
            return {}
        try:
            import json

            data = cast(dict[str, Any], json.loads(raw))
            limits: dict[str, int] = {}
            for k in ("qps", "vectors", "storage_gb"):
                if k in data:
                    try:
                        limits[k] = int(data[k])
                    except Exception:
                        continue
            return limits
        except Exception:
            return {}

    @staticmethod
    async def set_limits(tenant_id: str, limits: dict[str, int], ttl_seconds: int = 300) -> None:
        client = redis_manager.cache
        key = make_tenant_key_safe(tenant_id, "quota", "limits")
        import json

        await client.set(key, json.dumps(limits), ex=ttl_seconds)

    @staticmethod
    async def get_qps_limit(tenant_id: str, default_qps: int = 50) -> int:
        limits = await QuotaService.get_limits(tenant_id)
        try:
            return int(limits.get("qps", default_qps))
        except Exception:
            return default_qps


quota_service = QuotaService()
