"""Unit tests for authentication dependencies."""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.auth import (
    get_tenant_id_from_header,
    get_token_from_header,
    validate_token_and_tenant,
)
from app.utils.jwt import create_access_token


class TestGetTokenFromHeader:
    """Test extracting token from Authorization header."""

    @pytest.mark.asyncio
    async def test_extract_valid_bearer_token(self):
        """Test extracting valid Bearer token."""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        authorization = f"Bearer {token}"

        extracted = await get_token_from_header(authorization=authorization)
        assert extracted == token

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self):
        """Test missing Authorization header."""
        with pytest.raises(HTTPException) as exc_info:
            await get_token_from_header(authorization=None)

        assert exc_info.value.status_code == 401
        assert "Missing Authorization header" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_authorization_format_no_bearer(self):
        """Test invalid Authorization header without Bearer prefix."""
        with pytest.raises(HTTPException) as exc_info:
            await get_token_from_header(authorization="token123")

        assert exc_info.value.status_code == 401
        assert "Invalid Authorization header format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_authorization_format_wrong_scheme(self):
        """Test invalid Authorization header with wrong scheme."""
        with pytest.raises(HTTPException) as exc_info:
            await get_token_from_header(authorization="Basic token123")

        assert exc_info.value.status_code == 401
        assert "Invalid Authorization header format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_case_insensitive_bearer(self):
        """Test Bearer keyword is case-insensitive."""
        token = "test_token"
        authorization = f"bearer {token}"

        extracted = await get_token_from_header(authorization=authorization)
        assert extracted == token


class TestGetTenantIdFromHeader:
    """Test extracting tenant_id from X-Tenant-ID header."""

    @pytest.mark.asyncio
    async def test_extract_valid_tenant_id(self):
        """Test extracting valid UUID tenant_id."""
        tenant_id = uuid4()
        extracted = await get_tenant_id_from_header(x_tenant_id=str(tenant_id))

        assert extracted == tenant_id

    @pytest.mark.asyncio
    async def test_missing_tenant_id_header(self):
        """Test missing X-Tenant-ID header."""
        with pytest.raises(HTTPException) as exc_info:
            await get_tenant_id_from_header(x_tenant_id=None)

        assert exc_info.value.status_code == 400
        assert "Missing X-Tenant-ID header" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_tenant_id_format(self):
        """Test invalid UUID format in X-Tenant-ID header."""
        with pytest.raises(HTTPException) as exc_info:
            await get_tenant_id_from_header(x_tenant_id="not-a-uuid")

        assert exc_info.value.status_code == 400
        assert "Invalid X-Tenant-ID format" in exc_info.value.detail


class TestValidateTokenAndTenant:
    """Test token and tenant validation."""

    @pytest.mark.asyncio
    async def test_valid_token_and_matching_tenant(self):
        """Test valid token with matching tenant_id."""
        tenant_id = uuid4()
        token = create_access_token(tenant_id=tenant_id)

        validated_id = await validate_token_and_tenant(token=token, header_tenant_id=tenant_id)
        assert validated_id == tenant_id

    @pytest.mark.asyncio
    async def test_tenant_id_mismatch(self):
        """Test token tenant_id doesn't match header."""
        token_tenant_id = uuid4()
        header_tenant_id = uuid4()
        token = create_access_token(tenant_id=token_tenant_id)

        with pytest.raises(HTTPException) as exc_info:
            await validate_token_and_tenant(token=token, header_tenant_id=header_tenant_id)

        assert exc_info.value.status_code == 403
        assert "does not match" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_expired_token(self):
        """Test expired token raises 401."""
        from datetime import timedelta

        tenant_id = uuid4()
        token = create_access_token(tenant_id=tenant_id, expires_delta=timedelta(seconds=-1))

        with pytest.raises(HTTPException) as exc_info:
            await validate_token_and_tenant(token=token, header_tenant_id=tenant_id)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        """Test invalid token raises 401."""
        tenant_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await validate_token_and_tenant(token="invalid.token", header_tenant_id=tenant_id)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
