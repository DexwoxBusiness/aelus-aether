"""Code graph models (nodes, edges, embeddings)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text, JSON, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.repository import Repository


class CodeNode(Base):
    """Code node model (functions, classes, modules, etc.)."""

    __tablename__ = "code_nodes"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "repo_id", "qualified_name", name="uq_tenant_repo_node"
        ),
        Index("idx_nodes_tenant_repo", "tenant_id", "repo_id"),
        Index("idx_nodes_type", "node_type"),
        Index("idx_nodes_qualified_name", "qualified_name"),
        Index("idx_nodes_file_path", "file_path"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    repo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Node identity
    node_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'Function', 'Class', 'Module', 'File'
    qualified_name: Mapped[str] = mapped_column(String(500), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Location
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Code content
    source_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    docstring: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    complexity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata: Mapped[dict] = mapped_column(JSON, default={}, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="code_nodes")
    embeddings: Mapped[list["CodeEmbedding"]] = relationship(
        "CodeEmbedding", back_populates="node", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CodeNode(id={self.id}, type={self.node_type}, name={self.qualified_name})>"


class CodeEdge(Base):
    """Code edge model (relationships between nodes)."""

    __tablename__ = "code_edges"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "from_node_id",
            "to_node_id",
            "edge_type",
            name="uq_tenant_edge",
        ),
        Index("idx_edges_tenant", "tenant_id"),
        Index("idx_edges_from", "from_node_id"),
        Index("idx_edges_to", "to_node_id"),
        Index("idx_edges_type", "edge_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    from_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    to_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    edge_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'CALLS', 'IMPORTS', 'DEFINES', 'INHERITS', 'USES_API'
    metadata: Mapped[dict] = mapped_column(JSON, default={}, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<CodeEdge(id={self.id}, type={self.edge_type})>"


class CodeEmbedding(Base):
    """Code embedding model (vector embeddings for semantic search)."""

    __tablename__ = "code_embeddings"
    __table_args__ = (
        Index("idx_embeddings_tenant_repo", "tenant_id", "repo_id"),
        Index("idx_embeddings_node", "node_id"),
        Index("idx_embeddings_vector", "embedding", postgresql_using="ivfflat"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    repo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Chunk data
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Vector embedding (Voyage-Code-3: 1536 dimensions)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)

    # Metadata for filtering
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    node_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    node: Mapped["CodeNode"] = relationship("CodeNode", back_populates="embeddings")

    def __repr__(self) -> str:
        return f"<CodeEmbedding(id={self.id}, node_id={self.node_id})>"
