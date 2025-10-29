"""Ingestion schemas."""

from uuid import UUID

from pydantic import BaseModel


class IngestionRequest(BaseModel):
    """Schema for ingestion request."""

    tenant_id: UUID
    repo_id: UUID
    branch: str | None = "main"
    file_patterns: list[str] | None = None  # e.g., ["*.py", "*.ts"]
    # Optional namespace for AAET-24 validation: {tenant}:{org}/{repo}:{branch}:{type}
    namespace: str | None = None


class IngestionResponse(BaseModel):
    """Schema for ingestion response."""

    job_id: UUID
    status: str  # 'queued', 'processing', 'completed', 'failed'
    message: str | None = None
