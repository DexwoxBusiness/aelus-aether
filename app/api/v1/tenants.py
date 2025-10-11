"""Tenant management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantResponse

router = APIRouter()


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """
    Create a new tenant.
    
    This endpoint provisions a new tenant with:
    - Unique API key
    - Default quotas
    - Isolated namespace
    """
    # Check if tenant name already exists
    result = await db.execute(
        select(Tenant).where(Tenant.name == tenant_data.name)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with name '{tenant_data.name}' already exists",
        )
    
    # Create tenant
    tenant = Tenant(
        name=tenant_data.name,
        api_key=tenant_data.api_key,
        webhook_url=tenant_data.webhook_url,
        quotas=tenant_data.quotas or {"vectors": 500000, "qps": 50, "repos": 10},
        settings=tenant_data.settings or {},
    )
    
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)
    
    return tenant


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Get tenant by ID."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
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
    result = await db.execute(
        select(Tenant).offset(skip).limit(limit)
    )
    return list(result.scalars().all())
