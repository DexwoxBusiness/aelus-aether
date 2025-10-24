"""Cache utilities using Redis."""

import asyncio
import json
from typing import Any, Optional
from functools import wraps

import redis.asyncio as redis

from app.core.logging import get_logger
from app.core.redis import redis_manager
from app.utils.exceptions import CacheError

logger = get_logger(__name__)


class CacheService:
    """Service for caching data in Redis."""
    
    @staticmethod
    async def get(key: str) -> Optional[str]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
            
        Raises:
            CacheError: If Redis operation fails
        """
        try:
            value = await redis_manager.cache.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
            else:
                logger.debug(f"Cache miss: {key}")
            return value
        except redis.RedisError as e:
            logger.error(f"Redis error for key {key}: {e}")
            raise CacheError(f"Failed to get key {key}") from e
        except Exception as e:
            logger.error(f"Unexpected cache error for key {key}: {e}")
            raise CacheError(f"Unexpected error getting key {key}") from e
    
    @staticmethod
    async def set(key: str, value: str, ttl: int = 3600) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (default: 1 hour)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await redis_manager.cache.setex(key, ttl, value)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    @staticmethod
    async def delete(key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await redis_manager.cache.delete(key)
            logger.debug(f"Cache delete: {key}")
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    @staticmethod
    async def get_json(key: str) -> Optional[Any]:
        """
        Get JSON value from cache.
        
        Runs JSON decoding in thread pool to avoid blocking event loop.
        
        Args:
            key: Cache key
            
        Returns:
            Deserialized JSON value or None
        """
        value = await CacheService.get(key)
        if value:
            try:
                # Run JSON decoding in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, json.loads, value)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for key {key}: {e}")
        return None
    
    @staticmethod
    async def set_json(key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set JSON value in cache.
        
        Runs JSON encoding in thread pool to avoid blocking event loop.
        
        Args:
            key: Cache key
            value: Value to serialize and cache
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Run JSON encoding in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            json_value = await loop.run_in_executor(None, json.dumps, value)
            return await CacheService.set(key, json_value, ttl)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON encode error for key {key}: {e}")
            return False


def cached(ttl: int = 3600, key_prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache key
        
    Usage:
        @cached(ttl=300, key_prefix="user")
        async def get_user(user_id: str):
            return {"id": user_id, "name": "John"}
    
    TODO (AAET-15): Add tenant context to cache keys for multi-tenant isolation
    When AAET-15 is implemented, cache keys should include tenant_id prefix
    to prevent cross-tenant cache pollution.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # TODO (AAET-15): Extract tenant_id from request context and prefix key
            # tenant_id = get_current_tenant()  # From request context
            # key_parts = [tenant_id, key_prefix, func.__name__]
            
            # Build cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(filter(None, key_parts))
            
            # Try to get from cache (fail gracefully on cache errors)
            try:
                cached_value = await CacheService.get_json(cache_key)
                if cached_value is not None:
                    return cached_value
            except CacheError:
                logger.warning(f"Cache get failed for {cache_key}, executing function")
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Try to cache result (fail gracefully)
            try:
                await CacheService.set_json(cache_key, result, ttl)
            except CacheError:
                logger.warning(f"Cache set failed for {cache_key}")
            
            return result
        
        return wrapper
    return decorator


# Global cache service instance
cache = CacheService()
