"""Integration tests for Admin Tenant Onboarding (AAET-28)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import set_tenant_context
from app.models.tenant import Tenant
from app.utils.security import verify_api_key


@pytest.mark.asyncio
@pytest.mark.integration
class TestAdminTenantOnboarding:
    """Test admin tenant onboarding flow (AAET-28)."""

    async def test_create_tenant_success(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test successful tenant creation via admin endpoint."""
        # Set admin key in environment for this test
        admin_key = "test-admin-key-12345"
        settings.admin_api_key = admin_key

        headers = {"X-Admin-Key": admin_key}
        payload = {
            "name": "Test Company",
            "webhook_url": "https://test.com/webhook",
            "quotas": {"vectors": 1000000, "qps": 100, "storage_gb": 200, "repos": 20},
            "settings": {"feature_flags": {"beta": True}},
        }

        response = await async_client.post(
            f"{settings.api_prefix}/admin/tenants",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert data["name"] == "Test Company"
        assert "api_key" in data
        assert data["api_key"] is not None
        assert data["api_key"].startswith("aelus_")
        assert data["webhook_url"] == "https://test.com/webhook"
        assert data["quotas"]["vectors"] == 1000000
        assert data["quotas"]["qps"] == 100
        assert data["quotas"]["storage_gb"] == 200
        assert data["quotas"]["repos"] == 20
        assert data["settings"]["feature_flags"]["beta"] is True
        assert data["is_active"] is True
        assert "created_at" in data

        # Verify tenant in database
        tenant_id = data["id"]
        await set_tenant_context(db_session, tenant_id)
        result = await db_session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one()

        assert tenant.name == "Test Company"
        assert tenant.quotas["vectors"] == 1000000
        assert verify_api_key(data["api_key"], tenant.api_key_hash)

    async def test_create_tenant_with_default_quotas(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test tenant creation with default quotas when not specified."""
        admin_key = "test-admin-key-12345"
        settings.admin_api_key = admin_key

        headers = {"X-Admin-Key": admin_key}
        payload = {"name": "Default Quotas Company"}

        response = await async_client.post(
            f"{settings.api_prefix}/admin/tenants",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()

        # Verify default quotas are applied
        assert data["quotas"]["vectors"] == 500000
        assert data["quotas"]["qps"] == 50
        assert data["quotas"]["storage_gb"] == 100
        assert data["quotas"]["repos"] == 10

    async def test_create_tenant_idempotency(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that creating the same tenant twice returns existing tenant (idempotent)."""
        admin_key = "test-admin-key-12345"
        settings.admin_api_key = admin_key

        headers = {"X-Admin-Key": admin_key}
        payload = {"name": "Idempotent Company"}

        # First creation
        response1 = await async_client.post(
            f"{settings.api_prefix}/admin/tenants",
            json=payload,
            headers=headers,
        )

        assert response1.status_code == 201
        data1 = response1.json()
        assert data1["api_key"] is not None
        tenant_id1 = data1["id"]
        data1["api_key"]

        # Second creation with same name (idempotent)
        response2 = await async_client.post(
            f"{settings.api_prefix}/admin/tenants",
            json=payload,
            headers=headers,
        )

        # Should return 201 (or could be 200) with existing tenant
        assert response2.status_code == 201
        data2 = response2.json()

        # Should return same tenant ID
        assert data2["id"] == tenant_id1
        assert data2["name"] == "Idempotent Company"

        # API key should NOT be returned on subsequent calls (security)
        assert data2["api_key"] is None
        assert "message" in data2
        assert "already exists" in data2["message"].lower()

        # Verify only one tenant exists in database
        await set_tenant_context(db_session, tenant_id1)
        result = await db_session.execute(select(Tenant).where(Tenant.name == "Idempotent Company"))
        tenants = list(result.scalars().all())
        assert len(tenants) == 1

    async def test_create_tenant_without_admin_key(self, async_client: AsyncClient):
        """Test that tenant creation fails without admin key."""
        payload = {"name": "Unauthorized Company"}

        response = await async_client.post(
            f"{settings.api_prefix}/admin/tenants",
            json=payload,
            # No X-Admin-Key header
        )

        assert response.status_code == 401
        assert "admin authentication required" in response.json()["detail"].lower()

    async def test_create_tenant_with_invalid_admin_key(self, async_client: AsyncClient):
        """Test that tenant creation fails with invalid admin key."""
        admin_key = "test-admin-key-12345"
        settings.admin_api_key = admin_key

        headers = {"X-Admin-Key": "wrong-key"}
        payload = {"name": "Invalid Auth Company"}

        response = await async_client.post(
            f"{settings.api_prefix}/admin/tenants",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 401
        assert "invalid admin credentials" in response.json()["detail"].lower()

    async def test_create_tenant_admin_key_not_configured(self, async_client: AsyncClient):
        """Test that tenant creation fails when admin key is not configured."""
        # Clear admin key
        settings.admin_api_key = None

        headers = {"X-Admin-Key": "any-key"}
        payload = {"name": "No Config Company"}

        response = await async_client.post(
            f"{settings.api_prefix}/admin/tenants",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 500
        assert "admin authentication not configured" in response.json()["detail"].lower()

    async def test_api_key_generation_uniqueness(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that each tenant gets a unique API key."""
        admin_key = "test-admin-key-12345"
        settings.admin_api_key = admin_key

        headers = {"X-Admin-Key": admin_key}

        # Create multiple tenants
        api_keys = []
        for i in range(3):
            payload = {"name": f"Unique Key Company {i}"}
            response = await async_client.post(
                f"{settings.api_prefix}/admin/tenants",
                json=payload,
                headers=headers,
            )
            assert response.status_code == 201
            data = response.json()
            api_keys.append(data["api_key"])

        # Verify all API keys are unique
        assert len(api_keys) == len(set(api_keys))
        assert all(key.startswith("aelus_") for key in api_keys)

    async def test_api_key_hash_storage(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test that API key is hashed before storage (not stored in plaintext)."""
        admin_key = "test-admin-key-12345"
        settings.admin_api_key = admin_key

        headers = {"X-Admin-Key": admin_key}
        payload = {"name": "Hash Test Company"}

        response = await async_client.post(
            f"{settings.api_prefix}/admin/tenants",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        plaintext_api_key = data["api_key"]
        tenant_id = data["id"]

        # Verify in database
        await set_tenant_context(db_session, tenant_id)
        result = await db_session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one()

        # API key hash should not equal plaintext key
        assert tenant.api_key_hash != plaintext_api_key

        # Hash should start with bcrypt prefix
        assert tenant.api_key_hash.startswith("$2b$")

        # Verify the hash can validate the plaintext key
        assert verify_api_key(plaintext_api_key, tenant.api_key_hash)

    async def test_tenant_namespace_initialization(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that tenant namespace is initialized on creation."""
        admin_key = "test-admin-key-12345"
        settings.admin_api_key = admin_key

        headers = {"X-Admin-Key": admin_key}
        payload = {"name": "Namespace Test Company"}

        response = await async_client.post(
            f"{settings.api_prefix}/admin/tenants",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        tenant_id = data["id"]

        # Verify tenant can be accessed with proper context
        await set_tenant_context(db_session, tenant_id)
        result = await db_session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one()

        assert tenant is not None
        assert str(tenant.id) == tenant_id

    async def test_quota_validation(self, async_client: AsyncClient):
        """Test that quotas are properly validated and merged with defaults."""
        admin_key = "test-admin-key-12345"
        settings.admin_api_key = admin_key

        headers = {"X-Admin-Key": admin_key}

        # Provide partial quotas
        payload = {
            "name": "Partial Quotas Company",
            "quotas": {"vectors": 2000000},  # Only specify vectors
        }

        response = await async_client.post(
            f"{settings.api_prefix}/admin/tenants",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()

        # Should have custom vectors but default other quotas
        assert data["quotas"]["vectors"] == 2000000
        assert data["quotas"]["qps"] == 50  # Default
        assert data["quotas"]["storage_gb"] == 100  # Default
        assert data["quotas"]["repos"] == 10  # Default


@pytest.mark.asyncio
@pytest.mark.integration
class TestTenantCredentials:
    """Test tenant credential generation and security."""

    async def test_api_key_format(self, async_client: AsyncClient):
        """Test that API key follows expected format."""
        admin_key = "test-admin-key-12345"
        settings.admin_api_key = admin_key

        headers = {"X-Admin-Key": admin_key}
        payload = {"name": "Format Test Company"}

        response = await async_client.post(
            f"{settings.api_prefix}/admin/tenants",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        api_key = data["api_key"]

        # Verify format: aelus_<32 alphanumeric characters>
        assert api_key.startswith("aelus_")
        key_part = api_key[6:]  # Remove "aelus_" prefix
        assert len(key_part) == 32
        assert key_part.isalnum()

    async def test_api_key_only_returned_once(self, async_client: AsyncClient):
        """Test that API key is only returned on initial creation."""
        admin_key = "test-admin-key-12345"
        settings.admin_api_key = admin_key

        headers = {"X-Admin-Key": admin_key}
        payload = {"name": "Once Only Company"}

        # First creation
        response1 = await async_client.post(
            f"{settings.api_prefix}/admin/tenants",
            json=payload,
            headers=headers,
        )

        assert response1.status_code == 201
        data1 = response1.json()
        assert data1["api_key"] is not None

        # Idempotent call
        response2 = await async_client.post(
            f"{settings.api_prefix}/admin/tenants",
            json=payload,
            headers=headers,
        )

        assert response2.status_code == 201
        data2 = response2.json()
        assert data2["api_key"] is None  # Not returned on subsequent calls


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
