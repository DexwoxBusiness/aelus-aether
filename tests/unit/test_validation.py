"""Unit tests for validation utilities."""

import uuid

import pytest
import pytest_asyncio

from app.models.repository import Repository
from app.models.tenant import Tenant, User
from app.utils.exceptions import ValidationError
from app.utils.validation import (
    count_tenant_repositories,
    validate_can_create_repository,
    validate_repository_exists,
    validate_tenant_exists,
    validate_tenant_quota,
    validate_user_belongs_to_tenant,
)

# db_session fixture is provided by conftest.py


@pytest_asyncio.fixture
async def test_tenant(db_session):
    """Create a test tenant."""
    from app.utils.security import hash_api_key

    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Tenant Validation",
        api_key_hash=hash_api_key(f"aelus_validation_{uuid.uuid4().hex[:20]}"),
        quotas={"vectors": 1000, "qps": 10, "storage_gb": 10, "repos": 5},
        settings={},
        is_active=True,
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def test_user(db_session, test_tenant):
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        email=f"validation_{uuid.uuid4().hex[:8]}@test.com",
        password_hash="test_hash",
        role="member",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_repository(db_session, test_tenant):
    """Create a test repository."""
    repo = Repository(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="test-repo-validation",
        git_url="https://github.com/test/repo",
        branch="main",
    )
    db_session.add(repo)
    await db_session.flush()
    return repo


class TestValidateTenantExists:
    """Test validate_tenant_exists function."""

    @pytest.mark.asyncio
    async def test_validate_existing_tenant(self, db_session, test_tenant):
        """Test validating an existing tenant."""
        tenant = await validate_tenant_exists(db_session, test_tenant.id)
        assert tenant.id == test_tenant.id
        assert tenant.name == test_tenant.name

    @pytest.mark.asyncio
    async def test_validate_nonexistent_tenant(self, db_session):
        """Test validating a non-existent tenant."""
        fake_id = uuid.uuid4()
        with pytest.raises(ValidationError, match="not found"):
            await validate_tenant_exists(db_session, fake_id)

    @pytest.mark.asyncio
    async def test_validate_inactive_tenant(self, db_session):
        """Test validating an inactive tenant."""
        from app.utils.security import hash_api_key

        inactive_tenant = Tenant(
            id=uuid.uuid4(),
            name="Inactive Tenant",
            api_key_hash=hash_api_key(f"aelus_inactive_{uuid.uuid4().hex[:16]}"),
            quotas={},
            settings={},
            is_active=False,
        )
        db_session.add(inactive_tenant)
        await db_session.flush()

        with pytest.raises(ValidationError, match="inactive"):
            await validate_tenant_exists(db_session, inactive_tenant.id)


class TestValidateRepositoryExists:
    """Test validate_repository_exists function."""

    @pytest.mark.asyncio
    async def test_validate_existing_repository(self, db_session, test_repository):
        """Test validating an existing repository."""
        repo = await validate_repository_exists(db_session, test_repository.id)
        assert repo.id == test_repository.id
        assert repo.name == test_repository.name

    @pytest.mark.asyncio
    async def test_validate_nonexistent_repository(self, db_session):
        """Test validating a non-existent repository."""
        fake_id = uuid.uuid4()
        with pytest.raises(ValidationError, match="not found"):
            await validate_repository_exists(db_session, fake_id)

    @pytest.mark.asyncio
    async def test_validate_repository_with_tenant_ownership(
        self, db_session, test_repository, test_tenant
    ):
        """Test validating repository belongs to correct tenant."""
        repo = await validate_repository_exists(db_session, test_repository.id, test_tenant.id)
        assert repo.tenant_id == test_tenant.id

    @pytest.mark.asyncio
    async def test_validate_repository_wrong_tenant(self, db_session, test_repository):
        """Test validating repository with wrong tenant."""
        wrong_tenant_id = uuid.uuid4()
        with pytest.raises(ValidationError, match="does not belong"):
            await validate_repository_exists(db_session, test_repository.id, wrong_tenant_id)


class TestValidateUserBelongsToTenant:
    """Test validate_user_belongs_to_tenant function."""

    @pytest.mark.asyncio
    async def test_validate_user_correct_tenant(self, db_session, test_user, test_tenant):
        """Test validating user belongs to correct tenant."""
        user = await validate_user_belongs_to_tenant(db_session, test_user.id, test_tenant.id)
        assert user.id == test_user.id
        assert user.tenant_id == test_tenant.id

    @pytest.mark.asyncio
    async def test_validate_user_wrong_tenant(self, db_session, test_user):
        """Test validating user with wrong tenant."""
        wrong_tenant_id = uuid.uuid4()
        with pytest.raises(ValidationError, match="does not belong"):
            await validate_user_belongs_to_tenant(db_session, test_user.id, wrong_tenant_id)

    @pytest.mark.asyncio
    async def test_validate_nonexistent_user(self, db_session, test_tenant):
        """Test validating non-existent user."""
        fake_user_id = uuid.uuid4()
        with pytest.raises(ValidationError, match="not found"):
            await validate_user_belongs_to_tenant(db_session, fake_user_id, test_tenant.id)

    @pytest.mark.asyncio
    async def test_validate_inactive_user(self, db_session, test_tenant):
        """Test validating inactive user."""
        inactive_user = User(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            email=f"inactive_{uuid.uuid4().hex[:8]}@test.com",
            password_hash="test_hash",
            role="member",
            is_active=False,
        )
        db_session.add(inactive_user)
        await db_session.flush()

        with pytest.raises(ValidationError, match="inactive"):
            await validate_user_belongs_to_tenant(db_session, inactive_user.id, test_tenant.id)


class TestValidateTenantQuota:
    """Test validate_tenant_quota function."""

    @pytest.mark.asyncio
    async def test_quota_within_limit(self, db_session, test_tenant):
        """Test quota validation within limit."""
        result = await validate_tenant_quota(db_session, test_tenant.id, "repos", 3)
        assert result is True

    @pytest.mark.asyncio
    async def test_quota_at_limit(self, db_session, test_tenant):
        """Test quota validation at exact limit."""
        # Quota is 5, usage is 5 - should raise error
        with pytest.raises(ValidationError, match="exceeded quota"):
            await validate_tenant_quota(db_session, test_tenant.id, "repos", 5)

    @pytest.mark.asyncio
    async def test_quota_exceeded(self, db_session, test_tenant):
        """Test quota validation when exceeded."""
        with pytest.raises(ValidationError, match="exceeded quota"):
            await validate_tenant_quota(db_session, test_tenant.id, "repos", 10)

    @pytest.mark.asyncio
    async def test_quota_undefined_resource(self, db_session, test_tenant):
        """Test quota validation for undefined resource (should allow)."""
        result = await validate_tenant_quota(db_session, test_tenant.id, "undefined_resource", 1000)
        assert result is True


class TestCountTenantRepositories:
    """Test count_tenant_repositories function."""

    @pytest.mark.asyncio
    async def test_count_repositories(self, db_session, test_tenant, test_repository):
        """Test counting tenant repositories."""
        count = await count_tenant_repositories(db_session, test_tenant.id)
        assert count >= 1  # At least the test_repository

    @pytest.mark.asyncio
    async def test_count_repositories_empty(self, db_session):
        """Test counting repositories for tenant with none."""
        from app.utils.security import hash_api_key

        empty_tenant = Tenant(
            id=uuid.uuid4(),
            name="Empty Tenant",
            api_key_hash=hash_api_key(f"aelus_empty_{uuid.uuid4().hex[:16]}"),
            quotas={},
            settings={},
        )
        db_session.add(empty_tenant)
        await db_session.flush()

        count = await count_tenant_repositories(db_session, empty_tenant.id)
        assert count == 0


class TestValidateCanCreateRepository:
    """Test validate_can_create_repository function."""

    @pytest.mark.asyncio
    async def test_can_create_repository_within_quota(
        self, db_session, test_tenant, test_repository
    ):
        """Test can create repository when within quota."""
        # Tenant has quota of 5, currently has 1
        result = await validate_can_create_repository(db_session, test_tenant.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_cannot_create_repository_quota_exceeded(self, db_session):
        """Test cannot create repository when quota exceeded."""
        # Create tenant with low quota
        from app.utils.security import hash_api_key

        low_quota_tenant = Tenant(
            id=uuid.uuid4(),
            name="Low Quota Tenant",
            api_key_hash=hash_api_key(f"aelus_lowquota_{uuid.uuid4().hex[:14]}"),
            quotas={"repos": 1},
            settings={},
        )
        db_session.add(low_quota_tenant)
        await db_session.flush()

        # Create repository to reach quota
        repo = Repository(
            id=uuid.uuid4(),
            tenant_id=low_quota_tenant.id,
            name="quota-repo",
            git_url="https://github.com/test/quota",
            branch="main",
        )
        db_session.add(repo)
        await db_session.flush()

        # Should raise error when trying to validate creation
        with pytest.raises(ValidationError, match="exceeded quota"):
            await validate_can_create_repository(db_session, low_quota_tenant.id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
