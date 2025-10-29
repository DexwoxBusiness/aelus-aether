from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request, status

from app.utils.namespace import NamespaceComponents, parse_namespace


def get_tenant_from_auth(request: Request) -> UUID:
    """Extract authenticated tenant_id from request.state, normalized to UUID.

    Raises 401 if missing/invalid.
    """
    tenant_id_ctx = getattr(request.state, "tenant_id", None)
    if tenant_id_ctx is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return tenant_id_ctx if isinstance(tenant_id_ctx, UUID) else UUID(str(tenant_id_ctx))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant in auth context"
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
        ns = parse_namespace(namespace)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if ns.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Namespace tenant mismatch"
        )
    return ns
