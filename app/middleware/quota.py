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
    - Excludes admin/monitoring endpoints from quota tracking (e.g., /usage, /quota endpoints).
    """

    # Paths to exclude from quota tracking (admin/monitoring endpoints)
    EXCLUDED_PATHS = {"/usage", "/quota"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            return await call_next(request)

        # Skip quota tracking for admin/monitoring endpoints
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # Resolve QPS limit for this tenant
        qps_limit = await self._resolve_qps_limit(tenant_id, request)

        # Use explicit tenant-namespaced key for rate limiting
        # This ensures proper multi-tenant isolation
        rate_limit_key = f"tenant:{tenant_id}:ratelimit:api:qps"
        allowed, remaining = await rate_limiter.check_rate_limit(
            key=rate_limit_key, max_requests=qps_limit, window_seconds=60, tenant_isolated=False
        )

        if not allowed:
            # Get TTL for Retry-After header using tenant-safe key construction
            ttl = await self._get_rate_limit_ttl(tenant_id)

            headers = {
                "X-RateLimit-Limit": str(qps_limit),
                "X-RateLimit-Remaining": str(remaining),
            }

            if isinstance(ttl, int) and ttl > 0:
                headers["Retry-After"] = str(ttl)
                headers["X-RateLimit-Reset"] = str(ttl)

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

        # Increment monotonic API call counter for reporting (best-effort, after rate limit check)
        try:
            await quota_service.increment(str(tenant_id), "api_calls", 1)
            try:
                api_calls_total.labels(tenant_id=str(tenant_id)).inc()
            except Exception as e:
                logger.debug(
                    f"Failed to record metric for tenant {tenant_id}: {e}",
                    extra={"tenant_id": str(tenant_id)},
                )
        except Exception as e:
            logger.warning(
                f"Failed to increment api_calls for tenant {tenant_id}: {e}",
                extra={"tenant_id": str(tenant_id)},
            )

        # Process the request
        response = await call_next(request)

        # Add rate limit headers to successful responses
        response.headers["X-RateLimit-Limit"] = str(qps_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        # Add reset time (TTL of rate limit key)
        ttl = await self._get_rate_limit_ttl(tenant_id)
        if isinstance(ttl, int) and ttl > 0:
            response.headers["X-RateLimit-Reset"] = str(ttl)

        return response

    async def _resolve_qps_limit(self, tenant_id: str, request: Request) -> int:
        """
        Resolve QPS limit for a tenant with fallback chain.

        Priority order:
        1. request.state.tenant_qps_limit (explicit override for testing/special cases)
        2. Redis-cached quota limits from tenant.quotas['qps']
        3. Default fallback (50 QPS)

        Args:
            tenant_id: Tenant UUID
            request: Current request (for state override check)

        Returns:
            int: Resolved QPS limit
        """
        default_qps = 50

        # Check for explicit override (documented mechanism for testing)
        override = getattr(request.state, "tenant_qps_limit", None)
        if override is not None:
            try:
                return int(override)
            except (ValueError, TypeError):
                logger.warning(
                    f"Invalid tenant_qps_limit override: {override}, using default",
                    extra={"tenant_id": str(tenant_id)},
                )

        # Fetch from Redis cache
        try:
            qps_limit = await quota_service.get_qps_limit(str(tenant_id), default_qps=default_qps)
            return qps_limit
        except Exception as e:
            logger.warning(
                f"Failed to fetch QPS limit for tenant {tenant_id}: {e}, using default",
                extra={"tenant_id": str(tenant_id)},
            )
            return default_qps

    async def _get_rate_limit_ttl(self, tenant_id: str) -> int:
        """
        Get TTL for rate limit key using tenant ID directly.

        Args:
            tenant_id: Tenant ID string

        Returns:
            int: TTL in seconds, or -1 if unavailable
        """
        try:
            # Use tenant_id directly to construct the key (matches rate limit key format)
            rl_key = f"tenant:{tenant_id}:ratelimit:api:qps"
            ttl = await redis_manager.rate_limit.ttl(rl_key)
            return ttl if isinstance(ttl, int) else -1
        except Exception as e:
            logger.warning(
                f"Failed to get rate limit TTL for tenant {tenant_id}: {e}",
                extra={"tenant_id": tenant_id},
            )
            return -1

    def _is_excluded_path(self, path: str) -> bool:
        """
        Check if the request path should be excluded from quota tracking.

        Args:
            path: Request URL path

        Returns:
            bool: True if path should be excluded from quota tracking
        """
        # Check if path ends with any excluded suffix
        return any(path.endswith(excluded) for excluded in self.EXCLUDED_PATHS)
