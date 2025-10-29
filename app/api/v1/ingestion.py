"""Ingestion API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.ingestion import IngestionRequest, IngestionResponse
from app.utils.namespace import parse_namespace

router = APIRouter()


@router.post("/repository", response_model=IngestionResponse)
async def ingest_repository(
    request: IngestionRequest,
    db: AsyncSession = Depends(get_db),
    http_request: Request | None = None,
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
    # Validate namespace and tenant consistency (AAET-24)
    if http_request is not None:
        tenant_id_ctx = getattr(http_request.state, "tenant_id", None)
        if tenant_id_ctx is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )
        if str(request.tenant_id) != str(tenant_id_ctx):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant_id mismatch")
        if request.namespace:
            try:
                ns = parse_namespace(request.namespace)
            except ValueError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
            if str(ns.tenant_id) != str(tenant_id_ctx):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Namespace tenant mismatch"
                )

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
