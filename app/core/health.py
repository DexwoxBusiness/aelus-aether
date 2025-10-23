"""Health check utilities with caching for production scalability."""

from datetime import datetime, timedelta
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.exc import OperationalError


class HealthChecker:
    """
    Health checker with caching to avoid overwhelming database with health checks.
    
    In production, Kubernetes may check readiness every few seconds.
    Caching prevents excessive database queries.
    """
    
    def __init__(self, cache_ttl_seconds: int = 30):
        """
        Initialize health checker.
        
        Args:
            cache_ttl_seconds: Time-to-live for cached health check results
        """
        self._last_check: Optional[datetime] = None
        self._last_result: bool = False
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)
    
    async def check_database(self, engine: AsyncEngine) -> bool:
        """
        Check database connectivity with caching.
        
        Args:
            engine: SQLAlchemy async engine
            
        Returns:
            True if database is healthy, False otherwise
        """
        # Return cached result if still valid
        if self._last_check and datetime.now() - self._last_check < self._cache_ttl:
            logger.debug(f"Using cached health check result: {self._last_result}")
            return self._last_result
        
        # Perform actual health check
        try:
            async with engine.connect() as conn:
                await conn.execute("SELECT 1")
            self._last_result = True
            logger.debug("Database health check passed")
        except (OperationalError, ConnectionRefusedError, TimeoutError) as e:
            logger.warning(f"Database health check failed: {type(e).__name__}: {e}")
            self._last_result = False
        except Exception as e:
            logger.error(f"Unexpected error during health check: {type(e).__name__}: {e}")
            self._last_result = False
        
        self._last_check = datetime.now()
        return self._last_result
    
    def reset_cache(self) -> None:
        """Reset cached health check result (useful for testing)."""
        self._last_check = None
        self._last_result = False


# Global health checker instance
health_checker = HealthChecker(cache_ttl_seconds=30)
