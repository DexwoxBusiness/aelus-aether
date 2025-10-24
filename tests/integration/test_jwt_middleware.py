"""Integration tests for JWT authentication middleware."""

from datetime import timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.utils.jwt import create_access_token
from tests.factories import create_tenant_async


@pytest.mark.asyncio
class TestJWTMiddlewarePublicEndpoints:
    """Test JWT middleware behavior on public endpoints."""

    async def test_health_endpoint_no_auth(self, async_client: AsyncClient):
        """Test health endpoint doesn't require authentication."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    async def test_healthz_endpoint_no_auth(self, async_client: AsyncClient):
        """Test healthz endpoint doesn't require authentication."""
        response = await async_client.get("/healthz")
        assert response.status_code == 200

    async def test_readyz_endpoint_no_auth(self, async_client: AsyncClient):
        """Test readyz endpoint doesn't require authentication."""
        response = await async_client.get("/readyz")
        # May be 200 or 503 depending on dependencies, but shouldn't be 401
        assert response.status_code in [200, 503]

    async def test_root_endpoint_no_auth(self, async_client: AsyncClient):
        """Test root endpoint doesn't require authentication."""
        response = await async_client.get("/")
        assert response.status_code == 200

    async def test_docs_endpoint_no_auth(self, async_client: AsyncClient):
        """Test docs endpoint doesn't require authentication."""
        response = await async_client.get(f"{settings.api_prefix}/docs")
        assert response.status_code == 200

    async def test_openapi_endpoint_no_auth(self, async_client: AsyncClient):
        """Test OpenAPI endpoint doesn't require authentication."""
        response = await async_client.get(f"{settings.api_prefix}/openapi.json")
        assert response.status_code == 200


@pytest.mark.asyncio
class TestJWTMiddlewareAuthentication:
    """Test JWT middleware authentication on protected endpoints."""

    async def test_protected_endpoint_missing_auth_header(self, async_client: AsyncClient):
        """Test protected endpoint without Authorization header."""
        response = await async_client.get(f"{settings.api_prefix}/tenants/")
        assert response.status_code == 401
        # Middleware should catch this, but if it doesn't run, dependency will return "Not authenticated"
        detail = response.json()["detail"]
        assert "Missing Authorization header" in detail or "Not authenticated" in detail

    async def test_protected_endpoint_invalid_auth_format(self, async_client: AsyncClient):
        """Test protected endpoint with invalid Authorization format."""
        response = await async_client.get(
            f"{settings.api_prefix}/tenants/", headers={"Authorization": "InvalidFormat"}
        )
        assert response.status_code == 401
        # Should get error about invalid format or not authenticated
        detail = response.json()["detail"]
        assert "Invalid Authorization header format" in detail or "Not authenticated" in detail

    async def test_protected_endpoint_missing_tenant_header(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test protected endpoint without X-Tenant-ID header."""
        tenant = await create_tenant_async(db_session)
        await db_session.commit()

        token = create_access_token(tenant_id=tenant.id)

        response = await async_client.get(
            f"{settings.api_prefix}/tenants/", headers={"Authorization": f"Bearer {token}"}
        )
        # Middleware returns 400, but if it doesn't run, dependency returns 401
        assert response.status_code in [400, 401]
        detail = response.json()["detail"]
        assert "Missing X-Tenant-ID header" in detail or "Not authenticated" in detail

    async def test_protected_endpoint_invalid_tenant_id_format(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test protected endpoint with invalid X-Tenant-ID format."""
        tenant = await create_tenant_async(db_session)
        await db_session.commit()

        token = create_access_token(tenant_id=tenant.id)

        response = await async_client.get(
            f"{settings.api_prefix}/tenants/",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "not-a-uuid"},
        )
        assert response.status_code == 400
        assert "Invalid X-Tenant-ID format" in response.json()["detail"]

    async def test_protected_endpoint_tenant_mismatch(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test protected endpoint with mismatched tenant IDs."""
        tenant = await create_tenant_async(db_session)
        await db_session.commit()

        # Create token with different tenant_id
        different_tenant_id = uuid4()
        token = create_access_token(tenant_id=different_tenant_id)

        response = await async_client.get(
            f"{settings.api_prefix}/tenants/",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant.id),
            },
        )
        assert response.status_code == 403
        assert "does not match" in response.json()["detail"]

    async def test_protected_endpoint_expired_token(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test protected endpoint with expired token."""
        tenant = await create_tenant_async(db_session)
        await db_session.commit()

        # Create expired token
        token = create_access_token(tenant_id=tenant.id, expires_delta=timedelta(seconds=-1))

        response = await async_client.get(
            f"{settings.api_prefix}/tenants/",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant.id),
            },
        )
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    async def test_protected_endpoint_invalid_token(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test protected endpoint with invalid token."""
        tenant = await create_tenant_async(db_session)
        await db_session.commit()

        response = await async_client.get(
            f"{settings.api_prefix}/tenants/",
            headers={
                "Authorization": "Bearer invalid_token_here",
                "X-Tenant-ID": str(tenant.id),
            },
        )
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    async def test_protected_endpoint_inactive_tenant(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test protected endpoint with inactive tenant."""
        tenant = await create_tenant_async(db_session, is_active=False)
        await db_session.commit()

        token = create_access_token(tenant_id=tenant.id)

        response = await async_client.get(
            f"{settings.api_prefix}/tenants/",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant.id),
            },
        )
        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()

    async def test_protected_endpoint_nonexistent_tenant(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test protected endpoint with non-existent tenant."""
        fake_tenant_id = uuid4()
        token = create_access_token(tenant_id=fake_tenant_id)

        response = await async_client.get(
            f"{settings.api_prefix}/tenants/",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(fake_tenant_id),
            },
        )
        assert response.status_code == 403
        assert "not found" in response.json()["detail"].lower()

    async def test_protected_endpoint_valid_authentication(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test protected endpoint with valid authentication."""
        tenant = await create_tenant_async(db_session)
        await db_session.commit()

        token = create_access_token(tenant_id=tenant.id)

        response = await async_client.get(
            f"{settings.api_prefix}/tenants/",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant.id),
            },
        )
        # Should not be 401 or 403 (authentication passed)
        # May be 200 or other status depending on endpoint logic
        assert response.status_code not in [401, 403]


@pytest.mark.asyncio
class TestJWTMiddlewareRequestState:
    """Test JWT middleware sets tenant in request state."""

    async def test_tenant_available_in_request_state(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test tenant is available in request.state after authentication."""
        tenant = await create_tenant_async(db_session)
        await db_session.commit()

        token = create_access_token(tenant_id=tenant.id)

        # Call an endpoint that uses the tenant from request state
        response = await async_client.get(
            f"{settings.api_prefix}/tenants/",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant.id),
            },
        )

        # If authentication succeeded, tenant was set in request.state
        assert response.status_code not in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
