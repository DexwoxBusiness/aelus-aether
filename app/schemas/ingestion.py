"""Ingestion schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class IngestionRequest(BaseModel):
    """Schema for ingestion request."""

    tenant_id: UUID
    repo_id: UUID
    branch: str | None = "main"
    file_patterns: list[str] | None = None  # e.g., ["*.py", "*.ts"]


class IngestionResponse(BaseModel):
    """Schema for ingestion response."""

    job_id: UUID
    status: str  # 'queued', 'processing', 'completed', 'failed'
    message: str | None = None
