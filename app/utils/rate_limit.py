"""Rate limiting utilities using Redis with multi-tenant isolation."""

from app.core.logging import get_logger
from app.core.redis import redis_manager
from app.utils.tenant_context import get_current_tenant, make_tenant_key_safe

logger = get_logger(__name__)


class RateLimiter:
    """Rate limiter using Redis for distributed rate limiting."""

    @staticmethod
    async def check_rate_limit(
        key: str, max_requests: int, window_seconds: int, tenant_isolated: bool = True
    ) -> tuple[bool, int]:
        """
        Check if rate limit is exceeded using sliding window with tenant isolation.

        Args:
            key: Rate limit key (e.g., "user:123" or "ip:192.168.1.1")
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            tenant_isolated: If True, prefix key with tenant_id (default: True)

        Returns:
            Tuple of (allowed: bool, remaining: int)

        Note: If tenant_isolated=True but no tenant context is set, the rate limit
        is applied globally (without tenant prefix) with a warning.

        Example:
            # Tenant-isolated rate limit (default)
            allowed, remaining = await rate_limiter.check_rate_limit("api:calls", 100, 60)

            # Global rate limit (not tenant-specific)
            allowed, remaining = await rate_limiter.check_rate_limit(
                "system:health", 1000, 60, tenant_isolated=False
            )
        """
        # Apply tenant isolation if enabled
        if tenant_isolated:
            tenant_id = get_current_tenant()
            if tenant_id:
                key = make_tenant_key_safe(tenant_id, "ratelimit", key)
            else:
                logger.warning(
                    f"Tenant-isolated rate limit requested for {key} but no tenant context set. "
                    "Applying global rate limit. Call set_current_tenant() or use tenant_isolated=False."
                )
        try:
            client = redis_manager.rate_limit

            # Use Redis pipeline for atomic operations
            pipe = client.pipeline()

            # Increment counter
            pipe.incr(key)

            # Set expiry on first request
            pipe.expire(key, window_seconds)

            # Execute pipeline
            results = await pipe.execute()
            current_count = results[0]

            # Check if limit exceeded
            allowed = current_count <= max_requests
            remaining = max(0, max_requests - current_count)

            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for key: {key} ({current_count}/{max_requests})"
                )

            return allowed, remaining

        except Exception as e:
            logger.error(f"Rate limit check error for key {key}: {e}")
            # Fail open - allow request if Redis is down
            return True, max_requests

    @staticmethod
    async def reset_rate_limit(key: str) -> bool:
        """
        Reset rate limit counter for a key.

        Args:
            key: Rate limit key

        Returns:
            True if reset successful
        """
        try:
            await redis_manager.rate_limit.delete(key)
            logger.debug(f"Rate limit reset: {key}")
            return True
        except Exception as e:
            logger.error(f"Rate limit reset error for key {key}: {e}")
            return False

    @staticmethod
    async def get_remaining(key: str, max_requests: int) -> int:
        """
        Get remaining requests for a key.

        Args:
            key: Rate limit key
            max_requests: Maximum requests allowed

        Returns:
            Number of remaining requests
        """
        try:
            current = await redis_manager.rate_limit.get(key)
            if current is None:
                return max_requests
            return max(0, max_requests - int(current))
        except Exception as e:
            logger.error(f"Get remaining error for key {key}: {e}")
            return max_requests


# Global rate limiter instance
rate_limiter = RateLimiter()
