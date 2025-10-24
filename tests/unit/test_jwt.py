"""Unit tests for JWT utilities."""

from datetime import UTC, timedelta
from uuid import uuid4

import pytest
from jose import jwt

from app.config import settings
from app.utils.jwt import (
    TokenExpiredError,
    TokenInvalidError,
    create_access_token,
    decode_access_token,
    extract_tenant_id,
    extract_user_id,
    verify_token,
)


class TestCreateAccessToken:
    """Test JWT token creation."""

    def test_create_token_with_tenant_id(self):
        """Test creating token with tenant_id."""
        tenant_id = uuid4()
        token = create_access_token(tenant_id=tenant_id)

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode to verify claims
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["tenant_id"] == str(tenant_id)
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_token_with_user_id(self):
        """Test creating token with user_id."""
        tenant_id = uuid4()
        user_id = uuid4()
        token = create_access_token(tenant_id=tenant_id, user_id=user_id)

        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["tenant_id"] == str(tenant_id)
        assert payload["user_id"] == str(user_id)

    def test_create_token_with_additional_claims(self):
        """Test creating token with additional claims."""
        tenant_id = uuid4()
        additional_claims = {"role": "admin", "permissions": ["read", "write"]}
        token = create_access_token(tenant_id=tenant_id, additional_claims=additional_claims)

        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]

    def test_create_token_with_custom_expiration(self):
        """Test creating token with custom expiration."""
        tenant_id = uuid4()
        expires_delta = timedelta(minutes=5)
        token = create_access_token(tenant_id=tenant_id, expires_delta=expires_delta)

        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        assert "exp" in payload


class TestDecodeAccessToken:
    """Test JWT token decoding."""

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        tenant_id = uuid4()
        token = create_access_token(tenant_id=tenant_id)

        payload = decode_access_token(token)
        assert payload["tenant_id"] == str(tenant_id)
        assert payload["type"] == "access"

    def test_decode_expired_token(self):
        """Test decoding an expired token."""
        tenant_id = uuid4()
        # Create token that expires immediately
        token = create_access_token(tenant_id=tenant_id, expires_delta=timedelta(seconds=-1))

        with pytest.raises(TokenExpiredError, match="expired"):
            decode_access_token(token)

    def test_decode_invalid_signature(self):
        """Test decoding token with invalid signature."""
        tenant_id = uuid4()
        token = create_access_token(tenant_id=tenant_id)

        # Tamper with token
        tampered_token = token[:-10] + "tampered12"

        with pytest.raises(TokenInvalidError, match="Invalid token"):
            decode_access_token(tampered_token)

    def test_decode_malformed_token(self):
        """Test decoding malformed token."""
        with pytest.raises(TokenInvalidError, match="Invalid token"):
            decode_access_token("not.a.valid.token")

    def test_decode_token_missing_tenant_id(self):
        """Test decoding token without tenant_id claim."""
        from datetime import datetime

        # Create token manually without tenant_id
        exp_time = datetime.now(UTC) + timedelta(minutes=30)
        payload = {"type": "access", "exp": exp_time}
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

        with pytest.raises(TokenInvalidError, match="Missing tenant_id"):
            decode_access_token(token)

    def test_decode_token_wrong_type(self):
        """Test decoding token with wrong type."""
        from datetime import datetime

        # Create token with wrong type
        exp_time = datetime.now(UTC) + timedelta(minutes=30)
        payload = {
            "tenant_id": str(uuid4()),
            "type": "refresh",  # Wrong type
            "exp": exp_time,
        }
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

        with pytest.raises(TokenInvalidError, match="Invalid token type"):
            decode_access_token(token)


class TestVerifyToken:
    """Test token verification."""

    def test_verify_valid_token(self):
        """Test verifying a valid token."""
        tenant_id = uuid4()
        token = create_access_token(tenant_id=tenant_id)

        assert verify_token(token) is True

    def test_verify_expired_token(self):
        """Test verifying an expired token."""
        tenant_id = uuid4()
        token = create_access_token(tenant_id=tenant_id, expires_delta=timedelta(seconds=-1))

        assert verify_token(token) is False

    def test_verify_invalid_token(self):
        """Test verifying an invalid token."""
        assert verify_token("invalid.token.here") is False


class TestExtractTenantId:
    """Test extracting tenant_id from token."""

    def test_extract_tenant_id_success(self):
        """Test extracting tenant_id from valid token."""
        tenant_id = uuid4()
        token = create_access_token(tenant_id=tenant_id)

        extracted_id = extract_tenant_id(token)
        assert extracted_id == tenant_id

    def test_extract_tenant_id_expired_token(self):
        """Test extracting tenant_id from expired token."""
        tenant_id = uuid4()
        token = create_access_token(tenant_id=tenant_id, expires_delta=timedelta(seconds=-1))

        with pytest.raises(TokenExpiredError):
            extract_tenant_id(token)

    def test_extract_tenant_id_missing(self):
        """Test extracting tenant_id when missing."""
        from datetime import datetime

        exp_time = datetime.now(UTC) + timedelta(minutes=30)
        payload = {"type": "access", "exp": exp_time}
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

        with pytest.raises(TokenInvalidError, match="Missing tenant_id"):
            extract_tenant_id(token)

    def test_extract_tenant_id_invalid_format(self):
        """Test extracting tenant_id with invalid UUID format."""
        from datetime import datetime

        exp_time = datetime.now(UTC) + timedelta(minutes=30)
        payload = {
            "tenant_id": "not-a-uuid",
            "type": "access",
            "exp": exp_time,
        }
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

        with pytest.raises(TokenInvalidError, match="Invalid tenant_id format"):
            extract_tenant_id(token)


class TestExtractUserId:
    """Test extracting user_id from token."""

    def test_extract_user_id_success(self):
        """Test extracting user_id from valid token."""
        tenant_id = uuid4()
        user_id = uuid4()
        token = create_access_token(tenant_id=tenant_id, user_id=user_id)

        extracted_id = extract_user_id(token)
        assert extracted_id == user_id

    def test_extract_user_id_not_present(self):
        """Test extracting user_id when not present."""
        tenant_id = uuid4()
        token = create_access_token(tenant_id=tenant_id)

        extracted_id = extract_user_id(token)
        assert extracted_id is None

    def test_extract_user_id_invalid_format(self):
        """Test extracting user_id with invalid UUID format."""
        from datetime import datetime

        tenant_id = uuid4()
        exp_time = datetime.now(UTC) + timedelta(minutes=30)
        payload = {
            "tenant_id": str(tenant_id),
            "user_id": "not-a-uuid",
            "type": "access",
            "exp": exp_time,
        }
        token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

        # Should return None for invalid format
        extracted_id = extract_user_id(token)
        assert extracted_id is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
