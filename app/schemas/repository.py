"""Repository schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RepositoryBase(BaseModel):
    """Base repository schema."""

    name: str = Field(..., min_length=1, max_length=255)
    git_url: str
    branch: str | None = "main"
    repo_type: str | None = None  # 'frontend', 'backend', 'docs'
    framework: str | None = None  # 'react', 'fastapi', etc.
    language: str | None = None  # 'typescript', 'python', etc.
    metadata: dict | None = None


class RepositoryCreate(RepositoryBase):
    """Schema for creating a repository."""

    tenant_id: UUID


class RepositoryResponse(RepositoryBase):
    """Schema for repository response."""

    id: UUID
    tenant_id: UUID
    last_commit_sha: str | None
    last_synced_at: datetime | None
    sync_status: str
    created_at: datetime

    class Config:
        from_attributes = True
