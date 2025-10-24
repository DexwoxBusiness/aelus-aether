"""Tenant and User models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.utils.security import verify_api_key, verify_password

if TYPE_CHECKING:
    from app.models.repository import Repository


class Tenant(Base):
    """Tenant model for multi-tenancy."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    quotas: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default={"vectors": 500000, "qps": 50, "storage_gb": 100, "repos": 10},
        nullable=False,
    )
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="tenant", cascade="all, delete-orphan"
    )
    repositories: Mapped[list["Repository"]] = relationship(
        "Repository", back_populates="tenant", cascade="all, delete-orphan"
    )

    def verify_api_key(self, api_key: str) -> bool:
        """
        Verify an API key against the stored hash.

        Args:
            api_key: Plaintext API key to verify

        Returns:
            bool: True if API key is valid, False otherwise
        """
        return verify_api_key(api_key, self.api_key_hash)

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name})>"


class User(Base):
    """User model."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="member", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")

    def verify_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash.

        Args:
            password: Plaintext password to verify

        Returns:
            bool: True if password is valid, False otherwise
        """
        return verify_password(password, self.password_hash)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
