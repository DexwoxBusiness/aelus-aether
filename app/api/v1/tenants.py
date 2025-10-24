"""Tenant management endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantResponse
from app.utils.security import generate_api_key_with_hash

router = APIRouter()


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create a new tenant.

    This endpoint provisions a new tenant with:
    - Auto-generated secure API key (returned once)
    - Default quotas
    - Isolated namespace

    IMPORTANT: The API key is only returned in this response.
    Store it securely - it cannot be retrieved later.
    """
    # Check if tenant name already exists
    result = await db.execute(select(Tenant).where(Tenant.name == tenant_data.name))
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with name '{tenant_data.name}' already exists",
        )

    # Generate secure API key and hash
    # Check for hash collision (extremely rare but defensive programming)
    max_attempts = 3
    for attempt in range(max_attempts):
        api_key, api_key_hash = generate_api_key_with_hash()

        # Check if hash already exists (collision detection)
        hash_check = await db.execute(select(Tenant).where(Tenant.api_key_hash == api_key_hash))
        if hash_check.scalar_one_or_none() is None:
            break

        if attempt == max_attempts - 1:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate unique API key. Please try again.",
            )

    # Create tenant with hashed API key
    tenant = Tenant(
        name=tenant_data.name,
        api_key_hash=api_key_hash,
        webhook_url=tenant_data.webhook_url,
        quotas=tenant_data.quotas or {"vectors": 500000, "qps": 50, "storage_gb": 100, "repos": 10},
        settings=tenant_data.settings or {},
    )

    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    # Return tenant data with plaintext API key (only time it's shown)
    return {
        "id": tenant.id,
        "name": tenant.name,
        "api_key": api_key,  # Plaintext API key - only shown once!
        "webhook_url": tenant.webhook_url,
        "quotas": tenant.quotas,
        "settings": tenant.settings,
        "is_active": tenant.is_active,
        "created_at": tenant.created_at,
    }


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Get tenant by ID."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )

    return tenant


@router.get("/", response_model=list[TenantResponse])
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[Tenant]:
    """List all tenants."""
    result = await db.execute(select(Tenant).offset(skip).limit(limit))
    return list(result.scalars().all())
