"""enable_rls_tenant_isolation

Enable Row-Level Security (RLS) for tenant isolation on all tenant-scoped tables.

This migration implements AAET-23 by:
1. Enabling RLS on all tables with tenant_id
2. Creating policies that filter by current_setting('app.current_tenant_id')
3. Ensuring complete tenant data isolation at the database level

Revision ID: a3a9c19a1c85
Revises: 5f97db649d98
Create Date: 2025-10-25 15:42:24.553226

"""

from alembic import op
from sqlalchemy import DDL, text

# revision identifiers, used by Alembic.
revision = "a3a9c19a1c85"
down_revision = "5f97db649d98"
branch_labels = None
depends_on = None


def validate_table_exists(connection, table_name: str) -> bool:
    """
    Validate that a table exists in the database schema.

    This prevents SQL injection by querying information_schema rather than
    relying on hardcoded lists that could drift from actual schema.

    Args:
        connection: Database connection
        table_name: Name of table to validate

    Returns:
        bool: True if table exists, False otherwise
    """
    result = connection.execute(
        text(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = :table_name
            )
            """
        ),
        {"table_name": table_name},
    )
    return result.scalar()


def upgrade() -> None:
    """Enable RLS and create tenant isolation policies."""

    # List of tables that need tenant isolation
    # ============================================================================
    # DESIGN NOTE: Chunks Table
    # ============================================================================
    # There is NO separate "chunks" table in this RAG system architecture.
    # Instead, chunk data is stored in the "code_embeddings" table which contains:
    # - chunk_text: The actual text content of each chunk
    # - chunk_index: Position of chunk within the source code
    # - embedding: 1536-dimensional vector (Voyage-Code-3)
    # - node_id: Reference to the parent code node
    #
    # This design is MORE EFFICIENT for RAG because:
    # 1. Eliminates JOIN overhead during vector similarity search
    # 2. Keeps chunk text co-located with embeddings for faster retrieval
    # 3. Reduces database round-trips (single query returns text + metadata)
    # 4. Simplifies tenant isolation (one table instead of two)
    #
    # RLS on code_embeddings provides complete tenant isolation for:
    # - Vector similarity searches (SELECT with embedding distance)
    # - Chunk text retrieval (chunk_text column)
    # - All RAG operations (query → search → retrieve → generate)
    # ============================================================================
    tenant_tables = [
        "users",
        "repositories",
        "code_nodes",
        "code_edges",
        "code_embeddings",  # Contains chunk data + vectors for RAG
    ]

    # Get database connection for validation
    connection = op.get_bind()

    for table in tenant_tables:
        # ========================================================================
        # SECURITY: Validate table exists before using in SQL
        # ========================================================================
        # Query information_schema to ensure table exists
        # This prevents SQL injection and catches schema drift
        if not validate_table_exists(connection, table):
            raise ValueError(
                f"Table '{table}' does not exist in database schema. "
                f"Migration cannot proceed - check schema or table list."
            )

        # ========================================================================
        # 1. ENABLE ROW LEVEL SECURITY
        # ========================================================================
        # Use SQLAlchemy DDL for safer SQL generation
        op.execute(DDL(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))

        # ========================================================================
        # 2. CREATE SELECT POLICY - Only see your tenant's data
        # NULL check ensures no data access without tenant context
        # ========================================================================
        # Use DDL for safer SQL generation (table name already validated)
        op.execute(
            DDL(f"""
            CREATE POLICY {table}_tenant_isolation_select ON {table}
            FOR SELECT
            USING (
                tenant_id::text = current_setting('app.current_tenant_id', TRUE)
                AND current_setting('app.current_tenant_id', TRUE) IS NOT NULL
            )
        """)
        )

        # ========================================================================
        # 3. CREATE INSERT POLICY - Only insert with your tenant_id
        # NULL check prevents inserts without tenant context
        # ========================================================================
        op.execute(
            DDL(f"""
            CREATE POLICY {table}_tenant_isolation_insert ON {table}
            FOR INSERT
            WITH CHECK (
                tenant_id::text = current_setting('app.current_tenant_id', TRUE)
                AND current_setting('app.current_tenant_id', TRUE) IS NOT NULL
            )
        """)
        )

        # ========================================================================
        # 4. CREATE UPDATE POLICY - Only update your tenant's data
        # NULL check on both USING and WITH CHECK for complete protection
        # ========================================================================
        op.execute(
            DDL(f"""
            CREATE POLICY {table}_tenant_isolation_update ON {table}
            FOR UPDATE
            USING (
                tenant_id::text = current_setting('app.current_tenant_id', TRUE)
                AND current_setting('app.current_tenant_id', TRUE) IS NOT NULL
            )
            WITH CHECK (
                tenant_id::text = current_setting('app.current_tenant_id', TRUE)
                AND current_setting('app.current_tenant_id', TRUE) IS NOT NULL
            )
        """)
        )

        # ========================================================================
        # 5. CREATE DELETE POLICY - Only delete your tenant's data
        # NULL check prevents deletes without tenant context
        # ========================================================================
        op.execute(
            DDL(f"""
            CREATE POLICY {table}_tenant_isolation_delete ON {table}
            FOR DELETE
            USING (
                tenant_id::text = current_setting('app.current_tenant_id', TRUE)
                AND current_setting('app.current_tenant_id', TRUE) IS NOT NULL
            )
        """)
        )

    # ========================================================================
    # SPECIAL CASE: Tenants table (no tenant_id column)
    # ========================================================================
    # Validate tenants table exists
    if not validate_table_exists(connection, "tenants"):
        raise ValueError("Table 'tenants' does not exist in database schema")

    # Enable RLS but allow all operations (tenants manage themselves)
    op.execute(DDL("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY"))

    # Allow SELECT for all tenants (needed for JWT validation)
    op.execute(
        DDL("""
        CREATE POLICY tenants_select_all ON tenants
        FOR SELECT
        USING (TRUE)
    """)
    )

    # Only allow INSERT/UPDATE/DELETE on own tenant
    # NULL check added for consistency with other policies
    op.execute(
        DDL("""
        CREATE POLICY tenants_modify_own ON tenants
        FOR ALL
        USING (
            id::text = current_setting('app.current_tenant_id', TRUE)
            AND current_setting('app.current_tenant_id', TRUE) IS NOT NULL
        )
        WITH CHECK (
            id::text = current_setting('app.current_tenant_id', TRUE)
            AND current_setting('app.current_tenant_id', TRUE) IS NOT NULL
        )
    """)
    )


def downgrade() -> None:
    """Disable RLS and drop tenant isolation policies."""

    tenant_tables = [
        "users",
        "repositories",
        "code_nodes",
        "code_edges",
        "code_embeddings",
    ]

    for table in tenant_tables:
        # Drop policies
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation_select ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation_insert ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation_update ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation_delete ON {table}")

        # Disable RLS
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Drop tenants table policies
    op.execute("DROP POLICY IF EXISTS tenants_select_all ON tenants")
    op.execute("DROP POLICY IF EXISTS tenants_modify_own ON tenants")
    op.execute("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY")
