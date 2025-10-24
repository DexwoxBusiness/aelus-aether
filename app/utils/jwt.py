"""JWT token utilities for authentication.

This module provides utilities for:
- JWT token generation
- JWT token validation and decoding
- Token expiration handling

Uses python-jose for JWT operations with HS256 algorithm.
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TokenError(Exception):
    """Base exception for token-related errors."""

    pass


class TokenExpiredError(TokenError):
    """Raised when a token has expired."""

    pass


class TokenInvalidError(TokenError):
    """Raised when a token is invalid."""

    pass


def create_access_token(
    tenant_id: UUID,
    user_id: UUID | None = None,
    additional_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        tenant_id: Tenant UUID to include in token
        user_id: Optional user UUID to include in token
        additional_claims: Optional additional claims to include
        expires_delta: Optional custom expiration time

    Returns:
        str: Encoded JWT token

    Example:
        >>> token = create_access_token(
        ...     tenant_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        ...     user_id=UUID("123e4567-e89b-12d3-a456-426614174001")
        ... )
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_expiration_minutes)

    # Use UTC datetime without timezone info (JWT standard)
    now = datetime.utcnow()
    expire = now + expires_delta

    # Build claims
    claims: dict[str, Any] = {
        "tenant_id": str(tenant_id),
        "exp": expire,
        "iat": now,
        "type": "access",
    }

    if user_id:
        claims["user_id"] = str(user_id)

    if additional_claims:
        claims.update(additional_claims)

    # Encode token
    token: str = jwt.encode(claims, settings.secret_key, algorithm=settings.jwt_algorithm)
    logger.debug("Created access token", tenant_id=str(tenant_id), expires_at=expire.isoformat())

    return token


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        dict: Decoded token claims

    Raises:
        TokenExpiredError: If token has expired
        TokenInvalidError: If token is invalid or malformed

    Example:
        >>> claims = decode_access_token(token)
        >>> tenant_id = UUID(claims["tenant_id"])
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        # Validate token type
        if payload.get("type") != "access":
            raise TokenInvalidError("Invalid token type")

        # Validate required claims
        if "tenant_id" not in payload:
            raise TokenInvalidError("Missing tenant_id claim")

        logger.debug("Decoded access token", tenant_id=payload.get("tenant_id"))
        return payload

    except jwt.ExpiredSignatureError as e:
        logger.warning("Token expired", error=str(e))
        raise TokenExpiredError("Token has expired") from e
    except JWTError as e:
        logger.warning("Invalid token", error=str(e))
        raise TokenInvalidError(f"Invalid token: {e}") from e


def verify_token(token: str) -> bool:
    """
    Verify if a token is valid without decoding it.

    Args:
        token: JWT token string to verify

    Returns:
        bool: True if token is valid, False otherwise

    Example:
        >>> is_valid = verify_token(token)
    """
    try:
        decode_access_token(token)
        return True
    except (TokenExpiredError, TokenInvalidError):
        return False


def extract_tenant_id(token: str) -> UUID:
    """
    Extract tenant_id from a JWT token.

    Args:
        token: JWT token string

    Returns:
        UUID: Tenant ID from token

    Raises:
        TokenExpiredError: If token has expired
        TokenInvalidError: If token is invalid or missing tenant_id

    Example:
        >>> tenant_id = extract_tenant_id(token)
    """
    payload = decode_access_token(token)
    tenant_id_str = payload.get("tenant_id")

    if not tenant_id_str:
        raise TokenInvalidError("Missing tenant_id in token")

    try:
        return UUID(tenant_id_str)
    except (ValueError, TypeError) as e:
        raise TokenInvalidError(f"Invalid tenant_id format: {e}") from e


def extract_user_id(token: str) -> UUID | None:
    """
    Extract user_id from a JWT token if present.

    Args:
        token: JWT token string

    Returns:
        UUID | None: User ID from token, or None if not present

    Raises:
        TokenExpiredError: If token has expired
        TokenInvalidError: If token is invalid

    Example:
        >>> user_id = extract_user_id(token)
    """
    payload = decode_access_token(token)
    user_id_str = payload.get("user_id")

    if not user_id_str:
        return None

    try:
        return UUID(user_id_str)
    except (ValueError, TypeError) as e:
        logger.warning("Invalid user_id format in token", error=str(e))
        return None
