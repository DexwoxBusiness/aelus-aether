"""Cache utilities using Redis."""

import json
from typing import Any, Optional
from functools import wraps

from loguru import logger

from app.core.redis import redis_manager


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
        """
        try:
            value = await redis_manager.cache.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
            else:
                logger.debug(f"Cache miss: {key}")
            return value
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
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
        
        Args:
            key: Cache key
            
        Returns:
            Deserialized JSON value or None
        """
        value = await CacheService.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for key {key}: {e}")
        return None
    
    @staticmethod
    async def set_json(key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set JSON value in cache.
        
        Args:
            key: Cache key
            value: Value to serialize and cache
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            json_value = json.dumps(value)
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
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(filter(None, key_parts))
            
            # Try to get from cache
            cached_value = await CacheService.get_json(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await CacheService.set_json(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


# Global cache service instance
cache = CacheService()
