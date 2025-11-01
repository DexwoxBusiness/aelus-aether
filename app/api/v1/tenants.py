"""Tenant management endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_tenant
from app.core.database import get_db
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantResponse
from app.utils.quota import quota_service
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
    # Note: bcrypt hashes are salted, making collisions astronomically improbable
    # (probability < 2^-128). We accept this negligible risk rather than
    # introducing timing attack vectors through database collision checks.
    api_key, api_key_hash = generate_api_key_with_hash()

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
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
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
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[Tenant]:
    """List all tenants (requires authentication)."""
    result = await db.execute(select(Tenant).offset(skip).limit(limit))
    return list(result.scalars().all())


@router.get("/{tenant_id}/quota", response_model=dict[str, Any])
async def get_tenant_quota(
    tenant_id: str,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return current quotas for a tenant (from DB)."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return {"tenant_id": str(tenant.id), "quotas": tenant.quotas}


@router.put("/{tenant_id}/quota", response_model=dict[str, Any])
async def update_tenant_quota(
    tenant_id: str,
    quotas: dict[str, Any],
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update quotas for a tenant and refresh Redis cache of limits."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # Basic validation: keep only known keys
    allowed = {"vectors", "qps", "storage_gb", "repos"}
    new_quotas = {k: quotas[k] for k in quotas.keys() if k in allowed}
    if not new_quotas:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid quota keys")

    # Validate quota values
    for key, value in new_quotas.items():
        if not isinstance(value, int | float):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid quota value for {key}: must be a number",
            )
        if value < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid quota value for {key}: must be non-negative",
            )
        # Convert to int for consistency
        new_quotas[key] = int(value)

    # Update and persist
    tenant.quotas.update(new_quotas)
    await db.flush()
    await db.commit()

    # Refresh Redis cached limits (5 minutes TTL)
    try:
        await quota_service.set_limits(tenant_id, tenant.quotas, ttl_seconds=300)
    except Exception as e:
        # Log cache refresh failure but don't fail the request
        from app.core.logging import get_logger

        logger = get_logger(__name__)
        logger.warning(
            f"Failed to refresh quota cache for tenant {tenant_id}: {e}",
            extra={"tenant_id": tenant_id},
        )

    return {"tenant_id": str(tenant.id), "quotas": tenant.quotas}


@router.get("/{tenant_id}/usage", response_model=dict[str, Any])
async def get_tenant_usage(
    tenant_id: str,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return current usage counters for a tenant (from Redis)."""
    usage = await quota_service.get_usage(tenant_id)
    return {"tenant_id": tenant_id, "usage": usage}
