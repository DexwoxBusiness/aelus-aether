"""Tenant schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TenantBase(BaseModel):
    """Base tenant schema."""

    name: str = Field(..., min_length=1, max_length=255)
    webhook_url: str | None = None
    quotas: dict[str, Any] | None = None
    settings: dict[str, Any] | None = None


class TenantCreate(TenantBase):
    """Schema for creating a tenant.

    Note: API key is auto-generated and returned in the response.
    Do not include api_key in the request body.
    """

    pass


class TenantResponse(TenantBase):
    """Schema for tenant response."""

    id: UUID
    api_key: str | None = Field(
        None,
        description="API key (only returned on creation, stored as hash)",
    )
    is_active: bool
    created_at: datetime
    message: str | None = None

    class Config:
        from_attributes = True


class TenantQuotasPatch(BaseModel):
    quotas: dict[str, int]


class TenantDetailResponse(TenantResponse):
    usage: dict[str, int] | None = None


class TenantListResponse(BaseModel):
    items: list[TenantResponse]
    total: int
    page: int
    page_size: int
