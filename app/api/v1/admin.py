"""Admin endpoints for tenant management."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin_role
from app.core.database import get_admin_db
from app.models.tenant import Tenant
from app.schemas.tenant import (
    TenantCreate,
    TenantDetailResponse,
    TenantListResponse,
    TenantQuotasPatch,
    TenantResponse,
)
from app.utils.quota import quota_service
from app.utils.security import generate_api_key_with_hash

router = APIRouter()


@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant_admin(
    tenant_data: TenantCreate,
    _admin: Annotated[bool, Depends(require_admin_role)] = True,
    db: AsyncSession = Depends(get_admin_db),
) -> TenantResponse:
    """
    Create a new tenant (Admin only).

    This endpoint provisions a new tenant with:
    - Auto-generated UUID tenant_id
    - Secure API key (returned once, hashed with bcrypt)
    - Default quotas: max_vectors=500k, max_qps=50, max_storage_gb=100
    - Isolated namespace initialization

    **Idempotent**: If a tenant with the same name already exists,
    returns the existing tenant (without API key).

    **Admin Authentication Required**: Only users with admin role can create tenants.

    Args:
        tenant_data: Tenant creation data (name, optional quotas/settings)
        db: Database session
        _admin: Admin role verification (injected by dependency)

    Returns:
        dict: Tenant data with plaintext API key (only on first creation)

    Raises:
        HTTPException 401: If not authenticated as admin
        HTTPException 400: If invalid data provided

    Example:
        ```python
        POST /admin/tenants
        {
            "name": "Acme Corp",
            "quotas": {"vectors": 1000000, "qps": 100},
            "webhook_url": "https://acme.com/webhook"
        }

        Response (201 Created):
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Acme Corp",
            "api_key": "aelus_abc123...",  # Only shown once!
            "quotas": {"vectors": 1000000, "qps": 100, "storage_gb": 100, "repos": 10},
            "is_active": true,
            "created_at": "2025-11-02T00:00:00Z"
        }
        ```

    Note:
        The API key is only returned on initial creation. Store it securely.
        Subsequent calls with the same tenant name will return 200 OK without the API key.
    """
    # Enable admin mode for this transaction to allow RLS-bypassed admin ops
    await db.execute(text("SELECT set_config('app.admin_mode', 'on', TRUE)"))

    # Idempotency check: return existing tenant if name already exists
    result = await db.execute(select(Tenant).where(Tenant.name == tenant_data.name))
    existing = result.scalar_one_or_none()

    if existing:
        # Tenant already exists - return without API key (idempotent behavior)
        return TenantResponse(
            id=existing.id,
            name=existing.name,
            api_key=None,
            webhook_url=existing.webhook_url,
            quotas=existing.quotas,
            settings=existing.settings,
            is_active=existing.is_active,
            created_at=existing.created_at,
            message="Tenant already exists (idempotent)",
        )

    # Generate secure API key and hash
    # Note: bcrypt hashes are salted, making collisions astronomically improbable
    # (probability < 2^-128). We accept this negligible risk rather than
    # introducing timing attack vectors through database collision checks.
    api_key, api_key_hash = generate_api_key_with_hash()

    # Set default quotas if not provided
    default_quotas = {"vectors": 500000, "qps": 50, "storage_gb": 100, "repos": 10}
    quotas = tenant_data.quotas or default_quotas
    # Merge with defaults to ensure all keys are present
    final_quotas = {**default_quotas, **quotas}

    # Create tenant with hashed API key
    tenant = Tenant(
        name=tenant_data.name,
        api_key_hash=api_key_hash,
        webhook_url=tenant_data.webhook_url,
        quotas=final_quotas,
        settings=tenant_data.settings or {},
    )

    # Admin session bypasses RLS, so we can insert directly
    db.add(tenant)
    # Flush to persist and populate ORM defaults (id, created_at) without committing.
    # Commit is handled by get_admin_db in production; tests rely on outer rollback.
    await db.flush()

    # Initialize Redis quota limits (best-effort)
    await quota_service.refresh_cache(str(tenant.id), final_quotas)

    # Return tenant data with plaintext API key (only time it's shown)
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        api_key=api_key,  # Plaintext API key - only shown once!
        webhook_url=tenant.webhook_url,
        quotas=tenant.quotas,
        settings=tenant.settings,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
    )


@router.get("/tenants", response_model=TenantListResponse)
async def list_tenants_admin(
    _admin: Annotated[bool, Depends(require_admin_role)] = True,
    db: AsyncSession = Depends(get_admin_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> TenantListResponse:
    """List tenants with pagination (exclude soft-deleted)."""
    await db.execute(text("SELECT set_config('app.admin_mode', 'on', TRUE)"))

    # Total count (exclude deleted)
    total = (
        await db.execute(
            select(func.count()).select_from(Tenant).where(Tenant.deleted_at.is_(None))
        )
    ).scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Tenant)
        .where(Tenant.deleted_at.is_(None))
        .order_by(Tenant.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = list(result.scalars().all())

    return TenantListResponse(
        items=[TenantResponse.model_validate(i) for i in items],
        total=int(total or 0),
        page=page,
        page_size=page_size,
    )


@router.get("/tenants/{tenant_id}", response_model=TenantDetailResponse)
async def get_tenant_admin(
    tenant_id: UUID,
    _admin: Annotated[bool, Depends(require_admin_role)] = True,
    db: AsyncSession = Depends(get_admin_db),
) -> TenantDetailResponse:
    """Get tenant details including usage (exclude soft-deleted)."""
    await db.execute(text("SELECT set_config('app.admin_mode', 'on', TRUE)"))

    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.deleted_at.is_(None))
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    usage = await quota_service.get_usage(str(tenant.id))
    return TenantDetailResponse(
        id=tenant.id,
        name=tenant.name,
        api_key=None,
        webhook_url=tenant.webhook_url,
        quotas=tenant.quotas,
        settings=tenant.settings,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        usage=usage,
    )


@router.patch("/tenants/{tenant_id}/quotas", response_model=TenantResponse)
async def patch_tenant_quotas_admin(
    tenant_id: UUID,
    payload: TenantQuotasPatch,
    _admin: Annotated[bool, Depends(require_admin_role)] = True,
    db: AsyncSession = Depends(get_admin_db),
) -> TenantResponse:
    """Update tenant quotas (partial)."""
    await db.execute(text("SELECT set_config('app.admin_mode', 'on', TRUE)"))

    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.deleted_at.is_(None))
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # Set tenant context for RLS-safe update operations
    await db.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, TRUE)"),
        {"tenant_id": str(tenant_id)},
    )
    # Verify tenant context matches the target (defense-in-depth)
    try:
        ctx_res = await db.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
        current_tenant = ctx_res.scalar_one_or_none()
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Internal server error")
    if current_tenant != str(tenant_id):
        raise HTTPException(status_code=500, detail="Tenant context mismatch")

    # Validate and normalize quota updates via service
    try:
        updates = quota_service.validate_quota_updates(payload.quotas or {})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not updates:
        raise HTTPException(status_code=400, detail="No valid quota keys")

    tenant.quotas.update(updates)
    await db.flush()

    # Best-effort cache refresh
    await quota_service.refresh_cache(str(tenant_id), tenant.quotas)

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        api_key=None,
        webhook_url=tenant.webhook_url,
        quotas=tenant.quotas,
        settings=tenant.settings,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
    )


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_tenant_admin(
    tenant_id: UUID,
    _admin: Annotated[bool, Depends(require_admin_role)] = True,
    db: AsyncSession = Depends(get_admin_db),
) -> None:
    """Soft delete tenant (set deleted_at, deactivate)."""
    await db.execute(text("SELECT set_config('app.admin_mode', 'on', TRUE)"))

    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.deleted_at.is_(None))
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        # Treat soft-deleted as not found per acceptance criteria
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # Set tenant context for RLS-safe update operations
    await db.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, TRUE)"),
        {"tenant_id": str(tenant_id)},
    )
    # Verify tenant context matches the target (defense-in-depth)
    ctx_res = await db.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
    current_tenant = ctx_res.scalar_one_or_none()
    if current_tenant != str(tenant_id):
        raise HTTPException(status_code=500, detail="Tenant context mismatch")

    tenant.deleted_at = datetime.utcnow()
    tenant.is_active = False
    await db.flush()
    return None
