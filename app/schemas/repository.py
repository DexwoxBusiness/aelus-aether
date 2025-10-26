"""Repository schemas."""

from datetime import datetime
from typing import Any
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
    metadata: dict[str, Any] | None = None


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
        # Map ORM's metadata_ attribute to schema's metadata field
        populate_by_name = True

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: Any | None = None,
        **kwargs: Any,
    ) -> "RepositoryResponse":
        """Custom validation to handle metadata_ -> metadata mapping."""
        if hasattr(obj, "metadata_"):
            # Create dict from ORM object, mapping metadata_ to metadata
            data = {
                "id": obj.id,
                "tenant_id": obj.tenant_id,
                "name": obj.name,
                "git_url": obj.git_url,
                "branch": obj.branch,
                "repo_type": obj.repo_type,
                "framework": obj.framework,
                "language": obj.language,
                "last_commit_sha": obj.last_commit_sha,
                "last_synced_at": obj.last_synced_at,
                "sync_status": obj.sync_status,
                "metadata": obj.metadata_,  # Map metadata_ to metadata
                "created_at": obj.created_at,
            }
            return cls(**data)
        return super().model_validate(
            obj, strict=strict, from_attributes=from_attributes, context=context, **kwargs
        )
