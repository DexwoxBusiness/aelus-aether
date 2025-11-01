"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1 import admin, ingestion, repositories, retrieval, tenants

api_router = APIRouter()

# Include sub-routers
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
api_router.include_router(ingestion.router, prefix="/ingest", tags=["ingestion"])
api_router.include_router(retrieval.router, prefix="/retrieve", tags=["retrieval"])
