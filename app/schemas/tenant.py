"""Tenant schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TenantBase(BaseModel):
    """Base tenant schema."""

    name: str = Field(..., min_length=1, max_length=255)
    webhook_url: str | None = None
    quotas: dict | None = None
    settings: dict | None = None


class TenantCreate(TenantBase):
    """Schema for creating a tenant."""

    api_key: str = Field(..., min_length=32)


class TenantResponse(TenantBase):
    """Schema for tenant response."""

    id: UUID
    api_key: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
