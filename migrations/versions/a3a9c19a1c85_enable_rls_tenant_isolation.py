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

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a3a9c19a1c85"
down_revision = "5f97db649d98"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Enable RLS and create tenant isolation policies."""

    # List of tables that need tenant isolation
    tenant_tables = [
        "users",
        "repositories",
        "code_nodes",
        "code_edges",
        "code_embeddings",
    ]

    for table in tenant_tables:
        # ========================================================================
        # 1. ENABLE ROW LEVEL SECURITY
        # ========================================================================
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

        # ========================================================================
        # 2. CREATE SELECT POLICY - Only see your tenant's data
        # ========================================================================
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation_select ON {table}
            FOR SELECT
            USING (tenant_id::text = current_setting('app.current_tenant_id', TRUE))
        """)

        # ========================================================================
        # 3. CREATE INSERT POLICY - Only insert with your tenant_id
        # ========================================================================
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation_insert ON {table}
            FOR INSERT
            WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', TRUE))
        """)

        # ========================================================================
        # 4. CREATE UPDATE POLICY - Only update your tenant's data
        # ========================================================================
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation_update ON {table}
            FOR UPDATE
            USING (tenant_id::text = current_setting('app.current_tenant_id', TRUE))
            WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', TRUE))
        """)

        # ========================================================================
        # 5. CREATE DELETE POLICY - Only delete your tenant's data
        # ========================================================================
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation_delete ON {table}
            FOR DELETE
            USING (tenant_id::text = current_setting('app.current_tenant_id', TRUE))
        """)

    # ========================================================================
    # SPECIAL CASE: Tenants table (no tenant_id column)
    # ========================================================================
    # Enable RLS but allow all operations (tenants manage themselves)
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")

    # Allow SELECT for all tenants (needed for JWT validation)
    op.execute("""
        CREATE POLICY tenants_select_all ON tenants
        FOR SELECT
        USING (TRUE)
    """)

    # Only allow INSERT/UPDATE/DELETE on own tenant
    op.execute("""
        CREATE POLICY tenants_modify_own ON tenants
        FOR ALL
        USING (id::text = current_setting('app.current_tenant_id', TRUE))
        WITH CHECK (id::text = current_setting('app.current_tenant_id', TRUE))
    """)


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
