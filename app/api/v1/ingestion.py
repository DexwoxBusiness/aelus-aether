"""Ingestion API endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    ensure_namespace_for_tenant,
    ensure_request_tenant_matches,
    get_tenant_from_auth,
)
from app.core.database import get_db
from app.schemas.ingestion import IngestionRequest, IngestionResponse

router = APIRouter()


@router.post("/repository", response_model=IngestionResponse)
async def ingest_repository(
    request: IngestionRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_from_auth),
) -> IngestionResponse:
    """
    Trigger ingestion job for a repository.

    This endpoint will:
    1. Clone the repository
    2. Parse files using code-graph-rag
    3. Generate embeddings
    4. Store in PostgreSQL

    NOTE: Implementation in Phase 2 (AAET-87)
    """
    # Validate request body tenant matches authenticated tenant (AAET-24)
    ensure_request_tenant_matches(request.tenant_id, tenant_id)

    # Validate optional namespace format and tenant match
    ensure_namespace_for_tenant(request.namespace, tenant_id)

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Ingestion pipeline not yet implemented. Coming in Phase 2 (AAET-87)",
    )


@router.get("/job/{job_id}", response_model=dict[str, Any])
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get ingestion job status.

    NOTE: Implementation in Phase 2 (AAET-87)
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Job status tracking not yet implemented. Coming in Phase 2 (AAET-87)",
    )
