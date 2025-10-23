"""Redis connection management with connection pooling."""

from typing import Optional

import redis.asyncio as redis
from loguru import logger

from app.config import settings


class RedisManager:
    """
    Redis connection manager with separate clients for different use cases.
    
    - Queue: DB 0 (used by Celery)
    - Cache: DB 1 (application caching)
    - Rate Limiting: DB 2 (rate limit counters)
    """
    
    def __init__(self):
        """Initialize Redis manager."""
        self._queue_client: Optional[redis.Redis] = None
        self._cache_client: Optional[redis.Redis] = None
        self._rate_limit_client: Optional[redis.Redis] = None
    
    async def init_connections(self) -> None:
        """Initialize all Redis connections."""
        try:
            # Queue client (DB 0) - used by Celery
            self._queue_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=0,
                decode_responses=True,
                max_connections=50,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
            )
            
            # Cache client (DB 1) - application caching
            self._cache_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=1,
                decode_responses=True,
                max_connections=50,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
            )
            
            # Rate limit client (DB 2) - rate limiting
            self._rate_limit_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=2,
                decode_responses=True,
                max_connections=50,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
            )
            
            # Test connections
            await self._queue_client.ping()
            await self._cache_client.ping()
            await self._rate_limit_client.ping()
            
            logger.info("Redis connections initialized successfully")
            
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing Redis: {e}")
            raise
    
    async def close_connections(self) -> None:
        """Close all Redis connections."""
        try:
            if self._queue_client:
                await self._queue_client.aclose()
            if self._cache_client:
                await self._cache_client.aclose()
            if self._rate_limit_client:
                await self._rate_limit_client.aclose()
            
            logger.info("Redis connections closed")
            
        except Exception as e:
            logger.error(f"Error closing Redis connections: {e}")
    
    @property
    def queue(self) -> redis.Redis:
        """Get queue Redis client (DB 0)."""
        if not self._queue_client:
            raise RuntimeError("Redis queue client not initialized. Call init_connections() first.")
        return self._queue_client
    
    @property
    def cache(self) -> redis.Redis:
        """Get cache Redis client (DB 1)."""
        if not self._cache_client:
            raise RuntimeError("Redis cache client not initialized. Call init_connections() first.")
        return self._cache_client
    
    @property
    def rate_limit(self) -> redis.Redis:
        """Get rate limit Redis client (DB 2)."""
        if not self._rate_limit_client:
            raise RuntimeError("Redis rate limit client not initialized. Call init_connections() first.")
        return self._rate_limit_client
    
    async def health_check(self) -> dict[str, bool]:
        """
        Check health of all Redis connections.
        
        Returns:
            Dictionary with health status for each client
        """
        health = {
            "queue": False,
            "cache": False,
            "rate_limit": False,
        }
        
        try:
            if self._queue_client:
                await self._queue_client.ping()
                health["queue"] = True
        except Exception as e:
            logger.warning(f"Queue Redis health check failed: {e}")
        
        try:
            if self._cache_client:
                await self._cache_client.ping()
                health["cache"] = True
        except Exception as e:
            logger.warning(f"Cache Redis health check failed: {e}")
        
        try:
            if self._rate_limit_client:
                await self._rate_limit_client.ping()
                health["rate_limit"] = True
        except Exception as e:
            logger.warning(f"Rate limit Redis health check failed: {e}")
        
        return health


# Global Redis manager instance
redis_manager = RedisManager()
