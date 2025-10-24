"""Security utilities for password and API key hashing.

This module provides secure hashing and validation utilities for:
- API key generation and hashing
- Password hashing and verification
- Secure random token generation

Uses bcrypt for hashing with appropriate cost factors.
"""

import secrets
import string

import bcrypt

# API Key Configuration
API_KEY_PREFIX = "aelus_"
API_KEY_LENGTH = 32  # Length of random part (total will be prefix + length)
API_KEY_CHARSET = string.ascii_letters + string.digits

# Bcrypt Configuration
BCRYPT_ROUNDS = 12  # Cost factor for bcrypt (2^12 iterations)


def generate_api_key() -> str:
    """
    Generate a secure random API key.

    The API key format is: aelus_<32_random_chars>
    Example: aelus_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

    Returns:
        str: Generated API key (plaintext, to be shown to user once)

    Example:
        >>> api_key = generate_api_key()
        >>> print(api_key)
        aelus_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
    """
    random_part = "".join(secrets.choice(API_KEY_CHARSET) for _ in range(API_KEY_LENGTH))
    return f"{API_KEY_PREFIX}{random_part}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using bcrypt.

    Args:
        api_key: Plaintext API key to hash

    Returns:
        str: Bcrypt hash of the API key (safe to store in database)

    Example:
        >>> api_key = "aelus_abc123"
        >>> hashed = hash_api_key(api_key)
        >>> print(hashed)
        $2b$12$...
    """
    # Convert string to bytes
    api_key_bytes = api_key.encode("utf-8")

    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(api_key_bytes, salt)

    # Return as string
    return str(hashed.decode("utf-8"))


def verify_api_key(api_key: str, api_key_hash: str) -> bool:
    """
    Verify an API key against its hash.

    Args:
        api_key: Plaintext API key to verify
        api_key_hash: Stored bcrypt hash to verify against

    Returns:
        bool: True if API key matches hash, False otherwise

    Example:
        >>> api_key = "aelus_abc123"
        >>> hashed = hash_api_key(api_key)
        >>> verify_api_key(api_key, hashed)
        True
        >>> verify_api_key("wrong_key", hashed)
        False
    """
    try:
        api_key_bytes = api_key.encode("utf-8")
        hash_bytes = api_key_hash.encode("utf-8")
        return bool(bcrypt.checkpw(api_key_bytes, hash_bytes))
    except (ValueError, AttributeError):
        # Invalid hash format or encoding issues
        return False


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plaintext password to hash

    Returns:
        str: Bcrypt hash of the password (safe to store in database)

    Example:
        >>> password = "my_secure_password"
        >>> hashed = hash_password(password)
        >>> print(hashed)
        $2b$12$...
    """
    # Convert string to bytes
    password_bytes = password.encode("utf-8")

    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)

    # Return as string
    return str(hashed.decode("utf-8"))


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: Plaintext password to verify
        password_hash: Stored bcrypt hash to verify against

    Returns:
        bool: True if password matches hash, False otherwise

    Example:
        >>> password = "my_secure_password"
        >>> hashed = hash_password(password)
        >>> verify_password(password, hashed)
        True
        >>> verify_password("wrong_password", hashed)
        False
    """
    try:
        password_bytes = password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bool(bcrypt.checkpw(password_bytes, hash_bytes))
    except (ValueError, AttributeError):
        # Invalid hash format or encoding issues
        return False


def generate_api_key_with_hash() -> tuple[str, str]:
    """
    Generate an API key and its hash in one operation.

    This is a convenience function for tenant creation.

    Returns:
        Tuple[str, str]: (plaintext_api_key, api_key_hash)
            - plaintext_api_key: Show this to the user once
            - api_key_hash: Store this in the database

    Example:
        >>> api_key, api_key_hash = generate_api_key_with_hash()
        >>> print(f"API Key (show to user): {api_key}")
        >>> print(f"Hash (store in DB): {api_key_hash}")
    """
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)
    return api_key, api_key_hash


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a secure random token for various purposes.

    Args:
        length: Length of the token (default: 32)

    Returns:
        str: Secure random token

    Example:
        >>> token = generate_secure_token(16)
        >>> len(token)
        16
    """
    return secrets.token_urlsafe(length)
