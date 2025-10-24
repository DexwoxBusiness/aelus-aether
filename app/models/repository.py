"""Repository model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.code_graph import CodeNode
    from app.models.tenant import Tenant


class Repository(Base):
    """Repository model for multi-repo support."""

    __tablename__ = "repositories"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_tenant_repo_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    git_url: Mapped[str] = mapped_column(Text, nullable=False)
    branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    repo_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # 'frontend', 'backend', 'docs'
    framework: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # 'react', 'fastapi', etc.
    language: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # 'typescript', 'python', etc.
    last_commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sync_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True, default={}
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="repositories")
    code_nodes: Mapped[list["CodeNode"]] = relationship(
        "CodeNode", back_populates="repository", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Repository(id={self.id}, name={self.name}, type={self.repo_type})>"
