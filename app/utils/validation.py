"""Validation utilities for tenant and repository operations.

This module provides validation functions for:
- Tenant existence
- Repository ownership
- User authorization
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_context_logger
from app.models.repository import Repository
from app.models.tenant import Tenant, User
from app.utils.exceptions import ValidationError

logger = get_context_logger(__name__)


async def validate_tenant_exists(db: AsyncSession, tenant_id: str | UUID) -> Tenant:
    """
    Validate that a tenant exists.

    Args:
        db: Database session
        tenant_id: Tenant ID to validate

    Returns:
        Tenant: The tenant object if found

    Raises:
        ValidationError: If tenant doesn't exist or is inactive

    Example:
        >>> tenant = await validate_tenant_exists(db, "tenant-123")
        >>> print(tenant.name)
    """
    result = await db.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise ValidationError(f"Tenant {tenant_id} not found")

    if not tenant.is_active:
        raise ValidationError(f"Tenant {tenant_id} is inactive")

    # Soft-deleted tenants are considered invalid
    if getattr(tenant, "deleted_at", None) is not None:
        raise ValidationError(f"Tenant {tenant_id} is deleted")

    return tenant


async def validate_repository_exists(
    db: AsyncSession, repo_id: str | UUID, tenant_id: str | UUID | None = None
) -> Repository:
    """
    Validate that a repository exists and optionally belongs to a tenant.

    Args:
        db: Database session
        repo_id: Repository ID to validate
        tenant_id: Optional tenant ID to verify ownership

    Returns:
        Repository: The repository object if found

    Raises:
        ValidationError: If repository doesn't exist or doesn't belong to tenant

    Example:
        >>> repo = await validate_repository_exists(db, "repo-123", "tenant-123")
        >>> print(repo.name)
    """
    result = await db.execute(select(Repository).where(Repository.id == str(repo_id)))
    repository = result.scalar_one_or_none()

    if not repository:
        raise ValidationError(f"Repository {repo_id} not found")

    # Verify tenant ownership if tenant_id provided
    if tenant_id and str(repository.tenant_id) != str(tenant_id):
        raise ValidationError(
            f"Repository {repo_id} does not belong to tenant {tenant_id}. Access denied."
        )

    return repository


async def validate_user_belongs_to_tenant(
    db: AsyncSession, user_id: str | UUID, tenant_id: str | UUID
) -> User:
    """
    Validate that a user belongs to a specific tenant.

    Args:
        db: Database session
        user_id: User ID to validate
        tenant_id: Tenant ID to verify membership

    Returns:
        User: The user object if found and belongs to tenant

    Raises:
        ValidationError: If user doesn't exist or doesn't belong to tenant

    Example:
        >>> user = await validate_user_belongs_to_tenant(db, "user-123", "tenant-123")
        >>> print(user.email)
    """
    result = await db.execute(select(User).where(User.id == str(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise ValidationError(f"User {user_id} not found")

    if str(user.tenant_id) != str(tenant_id):
        raise ValidationError(
            f"User {user_id} does not belong to tenant {tenant_id}. Access denied."
        )

    if not user.is_active:
        raise ValidationError(f"User {user_id} is inactive")

    return user


async def validate_repository_ownership(
    db: AsyncSession, repo_id: str | UUID, tenant_id: str | UUID
) -> Repository:
    """
    Validate that a repository belongs to a tenant (alias for validate_repository_exists).

    This is a convenience function with a more descriptive name.

    Args:
        db: Database session
        repo_id: Repository ID
        tenant_id: Tenant ID that should own the repository

    Returns:
        Repository: The repository if it belongs to the tenant

    Raises:
        ValidationError: If repository doesn't belong to tenant

    Example:
        >>> repo = await validate_repository_ownership(db, "repo-123", "tenant-123")
    """
    return await validate_repository_exists(db, repo_id, tenant_id)


async def validate_tenant_quota(
    db: AsyncSession, tenant_id: str | UUID, resource: str, current_usage: int
) -> bool:
    """
    Validate that a tenant hasn't exceeded their quota for a resource.

    Args:
        db: Database session
        tenant_id: Tenant ID
        resource: Resource name (e.g., 'repos', 'vectors', 'storage_gb')
        current_usage: Current usage count

    Returns:
        bool: True if within quota, False if quota exceeded

    Raises:
        ValidationError: If tenant doesn't exist or quota exceeded

    Example:
        >>> is_within_quota = await validate_tenant_quota(db, "tenant-123", "repos", 5)
        >>> if not is_within_quota:
        ...     raise ValidationError("Repository quota exceeded")
    """
    tenant = await validate_tenant_exists(db, tenant_id)

    # Get quota for resource
    quota = tenant.quotas.get(resource)
    if quota is None:
        logger.warning(f"No quota defined for resource '{resource}' in tenant {tenant_id}")
        return True  # No quota = unlimited

    # Check if quota exceeded
    if current_usage >= quota:
        raise ValidationError(
            f"Tenant {tenant_id} has exceeded quota for '{resource}'. "
            f"Current: {current_usage}, Limit: {quota}"
        )

    return True


async def count_tenant_repositories(db: AsyncSession, tenant_id: str | UUID) -> int:
    """
    Count the number of repositories for a tenant.

    Args:
        db: Database session
        tenant_id: Tenant ID

    Returns:
        int: Number of repositories

    Example:
        >>> count = await count_tenant_repositories(db, "tenant-123")
        >>> print(f"Tenant has {count} repositories")
    """
    result = await db.execute(select(Repository).where(Repository.tenant_id == str(tenant_id)))
    repositories = result.scalars().all()
    return len(repositories)


async def validate_can_create_repository(db: AsyncSession, tenant_id: str | UUID) -> bool:
    """
    Validate that a tenant can create a new repository (within quota).

    Args:
        db: Database session
        tenant_id: Tenant ID

    Returns:
        bool: True if can create repository

    Raises:
        ValidationError: If quota exceeded

    Example:
        >>> can_create = await validate_can_create_repository(db, "tenant-123")
    """
    current_count = await count_tenant_repositories(db, tenant_id)
    return await validate_tenant_quota(db, tenant_id, "repos", current_count)
