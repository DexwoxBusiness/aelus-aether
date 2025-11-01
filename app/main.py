"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.exc import OperationalError

from app.api.v1 import api_router
from app.config import settings
from app.core.database import close_db, engine, init_db
from app.core.health import health_checker
from app.core.logging import configure_logging, get_logger
from app.core.redis import redis_manager
from app.middleware import JWTAuthMiddleware, RequestIDMiddleware
from app.middleware.quota import QuotaMiddleware

# Configure logging before any other imports that use logging
configure_logging(
    log_level=settings.log_level,
    json_logs=settings.json_logs,
    enable_sampling=settings.log_sampling,
    sample_rates={
        "debug": settings.log_sample_rate_debug,
        "info": settings.log_sample_rate_info,
        "warning": settings.log_sample_rate_warning,
        "error": settings.log_sample_rate_error,
        "critical": 1.0,  # Always log critical
    }
    if settings.log_sampling
    else None,
)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    logger.info(
        "Starting application",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Initialize Redis connections
    await redis_manager.init_connections()
    logger.info("Redis connections initialized")

    yield

    # Shutdown
    logger.info("Shutting down application")
    await close_db()
    logger.info("Database connections closed")

    await redis_manager.close_connections()
    logger.info("Redis connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-tenant, multi-repository RAG system for product intelligence",
    lifespan=lifespan,
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json",
)

# Request ID middleware (must be added first to track all requests)
app.add_middleware(RequestIDMiddleware)

# Quota middleware (must be after auth to access tenant_id)
app.add_middleware(QuotaMiddleware)

# JWT Authentication middleware (validates tokens and tenant context)
# Note: Added last so it runs first (middleware stack is LIFO)
app.add_middleware(JWTAuthMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health")
@app.get("/healthz")
async def health_check() -> JSONResponse:
    """
    Health check endpoint (liveness probe).

    Returns 200 if the application is running.
    Does not check dependencies.
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }
    )


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/readyz")
async def readiness_check() -> JSONResponse:
    """
    Readiness check endpoint (readiness probe).

    Returns 200 if the application is ready to serve traffic.
    Checks database connectivity with caching (30s TTL) to avoid overwhelming the database.

    In production, Kubernetes may check this endpoint every few seconds.
    Caching prevents excessive database queries.
    """
    try:
        # Check database health (cached)
        db_healthy = await health_checker.check_database(engine)

        # Check Redis health
        redis_health = await redis_manager.health_check()
        redis_healthy = all(redis_health.values())

        # Build checks response
        checks = {
            "database": "ok" if db_healthy else "failed",
            "redis": {
                "queue": "ok" if redis_health["queue"] else "failed",
                "cache": "ok" if redis_health["cache"] else "failed",
                "rate_limit": "ok" if redis_health["rate_limit"] else "failed",
            },
        }

        # Return 200 only if all checks pass
        if db_healthy and redis_healthy:
            return JSONResponse(
                content={
                    "status": "ready",
                    "service": settings.app_name,
                    "checks": checks,
                }
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "service": settings.app_name,
                    "checks": checks,
                },
            )
    except (OperationalError, ConnectionRefusedError, TimeoutError) as e:
        logger.error(f"Database connectivity issue during readiness check: {type(e).__name__}: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": settings.app_name,
                "checks": {
                    "database": "failed",
                },
                "error": f"Database connectivity issue: {type(e).__name__}",
            },
        )
    except Exception as e:
        logger.error(
            f"Unexpected error during readiness check: {type(e).__name__}: {e}", exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "service": settings.app_name,
                "checks": {
                    "database": "unknown",
                },
                "error": f"Unexpected error: {type(e).__name__}",
            },
        )


@app.get("/")
async def root() -> JSONResponse:
    """Root endpoint."""
    return JSONResponse(
        content={
            "message": f"Welcome to {settings.app_name}",
            "version": settings.app_version,
            "docs": f"{settings.api_prefix}/docs",
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
