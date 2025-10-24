"""tenant_schema_complete

Complete tenant schema implementation for AAET-15.

This migration creates:
- tenants table with api_key_hash and quotas
- users table with password_hash
- repositories table
- Updates code_nodes, code_edges, code_embeddings to match current models

Revision ID: 5f97db649d98
Revises: 001
Create Date: 2025-10-24 22:33:57.213427

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "5f97db649d98"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""

    # ========================================================================
    # 1. CREATE TENANTS TABLE
    # ========================================================================
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("api_key_hash", sa.String(length=255), nullable=False),
        sa.Column("webhook_url", sa.Text(), nullable=True),
        sa.Column(
            "quotas",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text(
                "'{\"vectors\": 500000, \"qps\": 50, \"storage_gb\": 100, \"repos\": 10}'"
            ),
        ),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("api_key_hash", name="uq_tenants_api_key_hash"),
    )

    # Create indexes for tenants
    op.create_index("idx_tenants_name", "tenants", ["name"])
    op.create_index("idx_tenants_is_active", "tenants", ["is_active"])

    # ========================================================================
    # 2. CREATE USERS TABLE
    # ========================================================================
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="member"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_users_tenant_id", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # Create indexes for users
    op.create_index("idx_users_tenant_id", "users", ["tenant_id"])
    op.create_index("idx_users_email", "users", ["email"])

    # ========================================================================
    # 3. CREATE REPOSITORIES TABLE
    # ========================================================================
    op.create_table(
        "repositories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("git_url", sa.Text(), nullable=False),
        sa.Column("branch", sa.String(length=100), nullable=False, server_default="main"),
        sa.Column("repo_type", sa.String(length=50), nullable=True),
        sa.Column("framework", sa.String(length=50), nullable=True),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column("last_commit_sha", sa.String(length=40), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("sync_status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column(
            "metadata_",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_repositories_tenant_id", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_tenant_repo_name"),
    )

    # Create indexes for repositories
    op.create_index("idx_repositories_tenant_id", "repositories", ["tenant_id"])
    op.create_index("idx_repositories_language", "repositories", ["language"])
    op.create_index("idx_repositories_sync_status", "repositories", ["sync_status"])

    # ========================================================================
    # 4. DROP OLD TABLES (from 001 migration)
    # ========================================================================
    op.drop_table("embeddings")
    op.drop_table("code_edges")
    op.drop_table("code_nodes")

    # ========================================================================
    # 5. CREATE CODE_NODES TABLE (updated schema)
    # ========================================================================
    op.create_table(
        "code_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_type", sa.String(length=50), nullable=False),
        sa.Column("qualified_name", sa.String(length=500), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=True),
        sa.Column("end_line", sa.Integer(), nullable=True),
        sa.Column("source_code", sa.Text(), nullable=True),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("docstring", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column("complexity", sa.Integer(), nullable=True),
        sa.Column(
            "metadata_",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_code_nodes_tenant_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["repo_id"], ["repositories.id"], name="fk_code_nodes_repo_id", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "repo_id", "qualified_name", name="uq_tenant_repo_node"),
    )

    # Create indexes for code_nodes
    op.create_index("idx_nodes_tenant_repo", "code_nodes", ["tenant_id", "repo_id"])
    op.create_index("idx_nodes_type", "code_nodes", ["node_type"])
    op.create_index("idx_nodes_qualified_name", "code_nodes", ["qualified_name"])
    op.create_index("idx_nodes_file_path", "code_nodes", ["file_path"])

    # ========================================================================
    # 6. CREATE CODE_EDGES TABLE (updated schema)
    # ========================================================================
    op.create_table(
        "code_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_type", sa.String(length=50), nullable=False),
        sa.Column(
            "metadata_",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_code_edges_tenant_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["from_node_id"], ["code_nodes.id"], name="fk_code_edges_from_node", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["to_node_id"], ["code_nodes.id"], name="fk_code_edges_to_node", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "from_node_id", "to_node_id", "edge_type", name="uq_tenant_edge"
        ),
    )

    # Create indexes for code_edges
    op.create_index("idx_edges_tenant", "code_edges", ["tenant_id"])
    op.create_index("idx_edges_from", "code_edges", ["from_node_id"])
    op.create_index("idx_edges_to", "code_edges", ["to_node_id"])
    op.create_index("idx_edges_type", "code_edges", ["edge_type"])

    # ========================================================================
    # 7. CREATE CODE_EMBEDDINGS TABLE (updated schema)
    # ========================================================================
    op.create_table(
        "code_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding", postgresql.ARRAY(sa.Float(), dimensions=1), nullable=False),
        sa.Column("metadata_", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("node_type", sa.String(length=50), nullable=True),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_code_embeddings_tenant_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["repo_id"],
            ["repositories.id"],
            name="fk_code_embeddings_repo_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["node_id"], ["code_nodes.id"], name="fk_code_embeddings_node_id", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Cast embedding column to vector(1536) type for Voyage AI
    op.execute(
        "ALTER TABLE code_embeddings ALTER COLUMN embedding TYPE vector(1536) "
        "USING embedding::vector(1536)"
    )

    # Create indexes for code_embeddings
    op.create_index("idx_embeddings_tenant_repo", "code_embeddings", ["tenant_id", "repo_id"])
    op.create_index("idx_embeddings_node", "code_embeddings", ["node_id"])

    # Create IVFFlat index for vector similarity search
    op.execute("""
        CREATE INDEX idx_embeddings_vector
        ON code_embeddings USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)


def downgrade() -> None:
    """Downgrade database schema."""

    # Drop new tables in reverse order
    op.drop_table("code_embeddings")
    op.drop_table("code_edges")
    op.drop_table("code_nodes")
    op.drop_table("repositories")
    op.drop_table("users")
    op.drop_table("tenants")

    # Recreate old tables from 001 migration
    # (This is a simplified recreation - in production you'd restore exact schema)
    op.create_table(
        "code_nodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("repo_id", sa.String(length=36), nullable=False),
        sa.Column("qualified_name", sa.Text(), nullable=False),
        sa.Column("node_type", sa.String(length=50), nullable=False),
        sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "code_edges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("from_node", sa.Text(), nullable=False),
        sa.Column("to_node", sa.Text(), nullable=False),
        sa.Column("edge_type", sa.String(length=50), nullable=False),
        sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("repo_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float(), dimensions=1), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
