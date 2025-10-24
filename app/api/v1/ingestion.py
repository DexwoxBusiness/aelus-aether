"""Ingestion endpoints (placeholder for Phase 2)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.ingestion import IngestionRequest, IngestionResponse

router = APIRouter()


@router.post("/repository", response_model=IngestionResponse)
async def ingest_repository(
    request: IngestionRequest,
    db: AsyncSession = Depends(get_db),
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
    # TODO: Implement in Phase 2
    # - Validate tenant and repository
    # - Queue Celery task
    # - Return job ID

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Ingestion pipeline not yet implemented. Coming in Phase 2 (AAET-87)",
    )


@router.get("/job/{job_id}", response_model=dict)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get ingestion job status.

    NOTE: Implementation in Phase 2 (AAET-87)
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Job status tracking not yet implemented. Coming in Phase 2 (AAET-87)",
    )
