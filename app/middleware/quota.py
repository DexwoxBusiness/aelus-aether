from __future__ import annotations

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import get_logger
from app.core.metrics import api_calls_total
from app.core.redis import redis_manager
from app.utils.quota import quota_service
from app.utils.rate_limit import rate_limiter

logger = get_logger(__name__)


class QuotaMiddleware(BaseHTTPMiddleware):
    """Middleware to track API call usage and enforce per-tenant API call quotas.

    Enforcement policy:
    - Always increments a monotonic per-tenant `api_calls` usage counter (for reporting).
    - Enforces per-tenant QPS limit using the existing RateLimiter (429 on exceed) and sets
      `Retry-After` header based on key TTL when available.
    - Only applies when request.state.tenant_id is present.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            return await call_next(request)

        # Increment monotonic API call counter (best-effort)
        try:
            await quota_service.increment(str(tenant_id), "api_calls", 1)
            try:
                api_calls_total.labels(tenant_id=str(tenant_id)).inc()
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Failed to increment api_calls for tenant {tenant_id}: {e}")

        # Enforce QPS using rate limiter with per-tenant isolation
        # Quota limit is taken from Tenant.quotas['qps'] cached by callers; if not available,
        # default to 50 as a sane fallback (matches default in models)
        # Determine QPS limit (Redis-cached limits > state override > default)
        qps_limit = 50
        try:
            limits_qps = await quota_service.get_qps_limit(str(tenant_id), default_qps=qps_limit)
            qps_limit = limits_qps
            # Allow explicit override via request.state if present
            override = getattr(request.state, "tenant_qps_limit", None)
            if override is not None:
                qps_limit = int(override)
        except Exception:
            qps_limit = 50

        allowed, remaining = await rate_limiter.check_rate_limit(
            key="api:qps", max_requests=qps_limit, window_seconds=60, tenant_isolated=True
        )
        if not allowed:
            # Attempt to read TTL from rate limit key to populate Retry-After
            try:
                # Rebuild the rate limit key the same way as rate_limiter
                # Note: tenant_isolated=True prefixes key internally; we reconstruct it here
                from app.utils.tenant_context import get_current_tenant, make_tenant_key_safe

                current_tenant = get_current_tenant()
                rl_key = (
                    make_tenant_key_safe(current_tenant, "ratelimit", "api:qps")
                    if current_tenant
                    else "api:qps"
                )
                ttl = await redis_manager.rate_limit.ttl(rl_key)
            except Exception:
                ttl = -1

            headers = {}
            if isinstance(ttl, int) and ttl > 0:
                headers["Retry-After"] = str(ttl)

            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={
                    "detail": "API quota exceeded. Please retry later.",
                    "retry_after": ttl if isinstance(ttl, int) and ttl > 0 else None,
                    "remaining": remaining,
                },
                headers=headers,
            )

        return await call_next(request)
