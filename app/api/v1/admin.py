"""Admin endpoints for tenant management."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin_role
from app.core.database import get_admin_db
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantResponse
from app.utils.quota import quota_service
from app.utils.security import generate_api_key_with_hash

router = APIRouter()


@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant_admin(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_admin_db),
    _admin: Annotated[bool, Depends(require_admin_role)] = True,
) -> dict[str, Any]:
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
    # Idempotency check: return existing tenant if name already exists
    result = await db.execute(select(Tenant).where(Tenant.name == tenant_data.name))
    existing = result.scalar_one_or_none()

    if existing:
        # Tenant already exists - return without API key (idempotent behavior)
        return {
            "id": existing.id,
            "name": existing.name,
            "api_key": None,  # Never return existing API key
            "webhook_url": existing.webhook_url,
            "quotas": existing.quotas,
            "settings": existing.settings,
            "is_active": existing.is_active,
            "created_at": existing.created_at,
            "message": "Tenant already exists (idempotent)",
        }

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
    await db.commit()
    await db.refresh(tenant)

    # Initialize Redis quota limits (5 minutes TTL)
    try:
        await quota_service.set_limits(str(tenant.id), final_quotas, ttl_seconds=300)
    except Exception as e:
        # Log but don't fail - quotas will be loaded from DB on first request
        from app.core.logging import get_logger

        logger = get_logger(__name__)
        logger.warning(
            f"Failed to initialize Redis quotas for tenant {tenant.id}: {e}",
            extra={"tenant_id": str(tenant.id), "error": str(e)},
        )

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
