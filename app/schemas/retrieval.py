"""Retrieval schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Schema for search request."""

    tenant_id: UUID
    query: str = Field(..., min_length=1)
    repo_ids: list[UUID] | None = None  # Filter by specific repos
    top_k: int = Field(default=10, ge=1, le=100)
    filters: dict | None = None  # Additional filters


class SearchResult(BaseModel):
    """Schema for a single search result."""

    node_id: UUID
    qualified_name: str
    node_type: str
    file_path: str
    source_code: str | None
    score: float
    metadata: dict | None = None


class SearchResponse(BaseModel):
    """Schema for search response."""

    results: list[SearchResult]
    total: int
    query: str
