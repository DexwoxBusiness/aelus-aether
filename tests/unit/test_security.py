"""Unit tests for security utilities."""

import pytest

from app.utils.security import (
    generate_api_key,
    generate_api_key_with_hash,
    generate_secure_token,
    hash_api_key,
    hash_password,
    verify_api_key,
    verify_password,
)


class TestAPIKeyGeneration:
    """Test API key generation functions."""

    def test_generate_api_key_format(self):
        """Test that generated API key has correct format."""
        api_key = generate_api_key()

        assert api_key.startswith("aelus_"), "API key should start with 'aelus_'"
        assert len(api_key) == 38, "API key should be 38 characters (aelus_ + 32 chars)"
        assert api_key[6:].isalnum(), "API key suffix should be alphanumeric"

    def test_generate_api_key_uniqueness(self):
        """Test that generated API keys are unique."""
        keys = [generate_api_key() for _ in range(100)]
        assert len(set(keys)) == 100, "All generated keys should be unique"

    def test_generate_api_key_with_hash(self):
        """Test generating API key with hash."""
        api_key, api_key_hash = generate_api_key_with_hash()

        assert api_key.startswith("aelus_"), "API key should have correct format"
        assert api_key_hash.startswith("$2b$"), "Hash should be bcrypt format"
        assert len(api_key_hash) == 60, "Bcrypt hash should be 60 characters"

        # Verify the hash matches the key
        assert verify_api_key(api_key, api_key_hash), "Hash should verify against key"


class TestAPIKeyHashing:
    """Test API key hashing and verification."""

    def test_hash_api_key(self):
        """Test API key hashing."""
        api_key = "aelus_test123456789012345678901234"
        hashed = hash_api_key(api_key)

        assert hashed.startswith("$2b$12$"), "Hash should use bcrypt with cost factor 12"
        assert len(hashed) == 60, "Bcrypt hash should be 60 characters"

    def test_verify_api_key_correct(self):
        """Test verifying correct API key."""
        api_key = "aelus_test123456789012345678901234"
        hashed = hash_api_key(api_key)

        assert verify_api_key(api_key, hashed), "Correct API key should verify"

    def test_verify_api_key_incorrect(self):
        """Test verifying incorrect API key."""
        api_key = "aelus_test123456789012345678901234"
        wrong_key = "aelus_wrong23456789012345678901234"
        hashed = hash_api_key(api_key)

        assert not verify_api_key(wrong_key, hashed), "Incorrect API key should not verify"

    def test_verify_api_key_invalid_hash(self):
        """Test verifying with invalid hash format."""
        api_key = "aelus_test123456789012345678901234"
        invalid_hash = "not_a_valid_hash"

        assert not verify_api_key(api_key, invalid_hash), "Invalid hash should return False"

    def test_hash_api_key_deterministic(self):
        """Test that same key produces different hashes (due to salt)."""
        api_key = "aelus_test123456789012345678901234"
        hash1 = hash_api_key(api_key)
        hash2 = hash_api_key(api_key)

        # Hashes should be different due to different salts
        assert hash1 != hash2, "Same key should produce different hashes (salted)"

        # But both should verify
        assert verify_api_key(api_key, hash1), "First hash should verify"
        assert verify_api_key(api_key, hash2), "Second hash should verify"


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "my_secure_password_123"
        hashed = hash_password(password)

        assert hashed.startswith("$2b$12$"), "Hash should use bcrypt with cost factor 12"
        assert len(hashed) == 60, "Bcrypt hash should be 60 characters"

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "my_secure_password_123"
        hashed = hash_password(password)

        assert verify_password(password, hashed), "Correct password should verify"

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "my_secure_password_123"
        wrong_password = "wrong_password_456"
        hashed = hash_password(password)

        assert not verify_password(wrong_password, hashed), "Incorrect password should not verify"

    def test_verify_password_invalid_hash(self):
        """Test verifying with invalid hash format."""
        password = "my_secure_password_123"
        invalid_hash = "not_a_valid_hash"

        assert not verify_password(password, invalid_hash), "Invalid hash should return False"

    def test_hash_password_deterministic(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "my_secure_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to different salts
        assert hash1 != hash2, "Same password should produce different hashes (salted)"

        # But both should verify
        assert verify_password(password, hash1), "First hash should verify"
        assert verify_password(password, hash2), "Second hash should verify"

    def test_password_case_sensitive(self):
        """Test that password verification is case-sensitive."""
        password = "MyPassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed), "Exact password should verify"
        assert not verify_password("mypassword123", hashed), "Different case should not verify"
        assert not verify_password("MYPASSWORD123", hashed), "Different case should not verify"


class TestSecureTokenGeneration:
    """Test secure token generation."""

    def test_generate_secure_token_default_length(self):
        """Test generating token with default length."""
        token = generate_secure_token()

        # URL-safe base64 encoding produces variable length
        # but should be around 43 characters for 32 bytes
        assert len(token) > 30, "Token should be reasonably long"
        assert len(token) < 50, "Token should not be excessively long"

    def test_generate_secure_token_custom_length(self):
        """Test generating token with custom length."""
        token = generate_secure_token(16)

        # Should be shorter than default
        assert len(token) < 30, "Shorter token should be generated"

    def test_generate_secure_token_uniqueness(self):
        """Test that generated tokens are unique."""
        tokens = [generate_secure_token() for _ in range(100)]
        assert len(set(tokens)) == 100, "All generated tokens should be unique"

    def test_generate_secure_token_url_safe(self):
        """Test that generated tokens are URL-safe."""
        token = generate_secure_token()

        # URL-safe base64 uses only: A-Z, a-z, 0-9, -, _
        import string

        allowed_chars = string.ascii_letters + string.digits + "-_"
        assert all(c in allowed_chars for c in token), "Token should be URL-safe"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
