"""Tenant context management utilities.

This module provides utilities for managing tenant context in requests:
- Getting current tenant from request state
- Validating tenant access
- Tenant-aware cache/rate limit key generation
"""

from contextvars import ContextVar
from uuid import UUID

from fastapi import Request

# Context variable for storing current tenant ID
_current_tenant_id: ContextVar[str | None] = ContextVar("current_tenant_id", default=None)


def set_current_tenant(tenant_id: str | UUID) -> None:
    """
    Set the current tenant ID in context.

    Args:
        tenant_id: Tenant ID to set (string or UUID)

    Example:
        >>> set_current_tenant("tenant-123")
        >>> get_current_tenant()
        'tenant-123'
    """
    tenant_id_str = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id
    _current_tenant_id.set(tenant_id_str)


def get_current_tenant() -> str | None:
    """
    Get the current tenant ID from context.

    Returns:
        str | None: Current tenant ID or None if not set

    Example:
        >>> set_current_tenant("tenant-123")
        >>> get_current_tenant()
        'tenant-123'
    """
    return _current_tenant_id.get()


def clear_current_tenant() -> None:
    """
    Clear the current tenant ID from context.

    Example:
        >>> set_current_tenant("tenant-123")
        >>> clear_current_tenant()
        >>> get_current_tenant()
        None
    """
    _current_tenant_id.set(None)


def get_tenant_from_request(request: Request) -> str | None:
    """
    Extract tenant ID from request state.

    Args:
        request: FastAPI request object

    Returns:
        str | None: Tenant ID from request state or None

    Example:
        >>> tenant_id = get_tenant_from_request(request)
        >>> if tenant_id:
        ...     set_current_tenant(tenant_id)
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    return str(tenant_id) if tenant_id is not None else None


def make_tenant_key(*parts: str) -> str:
    """
    Create a tenant-prefixed cache/rate limit key.

    Args:
        *parts: Key parts to join

    Returns:
        str: Tenant-prefixed key

    Raises:
        ValueError: If no tenant is set in context

    Example:
        >>> set_current_tenant("tenant-123")
        >>> make_tenant_key("cache", "user", "456")
        'tenant-123:cache:user:456'
    """
    tenant_id = get_current_tenant()
    if not tenant_id:
        raise ValueError(
            "No tenant context set. Call set_current_tenant() first or use make_tenant_key_safe()"
        )

    return ":".join([tenant_id, *parts])


def make_tenant_key_safe(tenant_id: str, *parts: str) -> str:
    """
    Create a tenant-prefixed key without requiring context.

    This is useful when you have the tenant_id directly and don't
    want to rely on context variables.

    Args:
        tenant_id: Tenant ID to use
        *parts: Key parts to join

    Returns:
        str: Tenant-prefixed key

    Example:
        >>> make_tenant_key_safe("tenant-123", "cache", "user", "456")
        'tenant-123:cache:user:456'
    """
    return ":".join([tenant_id, *parts])


def require_tenant() -> str:
    """
    Get current tenant ID, raising an error if not set.

    Returns:
        str: Current tenant ID

    Raises:
        ValueError: If no tenant is set in context

    Example:
        >>> set_current_tenant("tenant-123")
        >>> require_tenant()
        'tenant-123'
        >>> clear_current_tenant()
        >>> require_tenant()
        Traceback (most recent call last):
            ...
        ValueError: No tenant context set
    """
    tenant_id = get_current_tenant()
    if not tenant_id:
        raise ValueError(
            "No tenant context set. This operation requires a tenant context. "
            "Ensure the request includes X-Tenant-ID header."
        )
    return tenant_id
