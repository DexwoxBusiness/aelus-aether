"""Rate limiting utilities using Redis."""

from app.core.logging import get_logger
from app.core.redis import redis_manager

logger = get_logger(__name__)


class RateLimiter:
    """Rate limiter using Redis for distributed rate limiting."""

    @staticmethod
    async def check_rate_limit(
        key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check if rate limit is exceeded using sliding window.

        Args:
            key: Rate limit key (e.g., "user:123" or "ip:192.168.1.1")
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (allowed: bool, remaining: int)

        TODO (AAET-15): Add tenant context to rate limit keys for multi-tenant isolation
        When AAET-15 is implemented, rate limit keys should include tenant_id prefix
        to prevent cross-tenant rate limit interference.
        Example: tenant_key = f"{tenant_id}:{key}"
        """
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
