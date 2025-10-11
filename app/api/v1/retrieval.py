"""Retrieval endpoints (placeholder for Phase 4)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.retrieval import SearchRequest, SearchResponse

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def hybrid_search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """
    Hybrid search: vector + graph retrieval.
    
    This endpoint will:
    1. Vector search using pgvector
    2. Graph traversal for relationships
    3. Reranking with Cohere
    4. Return ranked results
    
    NOTE: Implementation in Phase 4 (AAET-46 to AAET-56)
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Hybrid search not yet implemented. Coming in Phase 4",
    )
