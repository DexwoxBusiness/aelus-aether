from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request, status

from app.utils.namespace import (
    NamespaceComponents,
    validate_namespace_for_tenant,
)


def get_tenant_from_auth(request: Request) -> UUID:
    """Extract authenticated tenant_id from request.state, normalized to UUID.

    Raises 401 if missing/invalid.
    """
    tenant_id_ctx = getattr(request.state, "tenant_id", None)
    if tenant_id_ctx is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return tenant_id_ctx if isinstance(tenant_id_ctx, UUID) else UUID(str(tenant_id_ctx))
    except (ValueError, AttributeError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid tenant in auth context: {str(e)}",
        )


def ensure_namespace_for_tenant(
    namespace: str | None, tenant_id: UUID
) -> NamespaceComponents | None:
    """Helper to validate optional namespace string.

    Returns parsed components or None if no namespace provided.
    Raises HTTPException 400 for invalid format, 403 for tenant mismatch.
    """
    if not namespace:
        return None
    try:
        # Reuse core validator (raises HTTPException 403 on tenant mismatch)
        return validate_namespace_for_tenant(namespace, tenant_id)
    except ValueError as e:
        # Invalid format -> 400
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def ensure_request_tenant_matches(body_tenant_id: UUID | str, auth_tenant_id: UUID) -> None:
    """Ensure tenant in request body matches authenticated tenant.

    Accepts both UUID and string representations. Raises 403 on mismatch or invalid format.
    """
    try:
        body_uuid = (
            body_tenant_id if isinstance(body_tenant_id, UUID) else UUID(str(body_tenant_id))
        )
        if body_uuid != auth_tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant_id mismatch")
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid tenant_id format in request",
        )
