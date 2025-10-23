"""Redis connection management with connection pooling."""

import asyncio
from typing import Optional

import redis.asyncio as redis
from loguru import logger

from app.config import settings
from app.core.redis_config import RedisConfig, RedisClientConfig


class RedisManager:
    """
    Redis connection manager with separate clients for different use cases.
    
    Uses dependency injection for configuration to enable testability.
    
    - Queue: DB 0 (used by Celery)
    - Cache: DB 1 (application caching)
    - Rate Limiting: DB 2 (rate limit counters)
    """
    
    def __init__(self, config: RedisConfig):
        """
        Initialize Redis manager with configuration.
        
        Args:
            config: Redis configuration for all clients
        """
        self.config = config
        self._queue_client: Optional[redis.Redis] = None
        self._cache_client: Optional[redis.Redis] = None
        self._rate_limit_client: Optional[redis.Redis] = None
    
    async def init_connections(self) -> None:
        """
        Initialize all Redis connections with retry logic.
        
        Implements exponential backoff retry for transient failures.
        """
        max_retries = 3
        base_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                await self._create_connections()
                logger.info("Redis connections initialized successfully")
                return
            except redis.ConnectionError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Redis connection attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Failed to connect to Redis after {max_retries} attempts: {e}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error initializing Redis: {e}")
                raise
    
    def _create_client(self, client_config: RedisClientConfig) -> redis.Redis:
        """
        Create a Redis client from configuration.
        
        Args:
            client_config: Configuration for the Redis client
            
        Returns:
            Configured Redis client
        """
        return redis.Redis(**client_config.to_dict())
    
    async def _create_connections(self) -> None:
        """Create Redis client connections using configuration."""
        try:
            # Create clients from configuration
            self._queue_client = self._create_client(self.config.queue_config)
            self._cache_client = self._create_client(self.config.cache_config)
            self._rate_limit_client = self._create_client(self.config.rate_limit_config)
            
            # Test connections
            await self._queue_client.ping()
            await self._cache_client.ping()
            await self._rate_limit_client.ping()
            
        except redis.ConnectionError:
            # Re-raise to trigger retry logic
            raise
        except Exception:
            # Re-raise unexpected errors
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


# Global Redis manager instance with configuration from settings
redis_manager = RedisManager(
    config=RedisConfig.from_settings(
        host=settings.redis_host,
        port=settings.redis_port
    )
)
