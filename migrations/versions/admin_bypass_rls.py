"""admin_bypass_rls

Add RLS bypass policies for admin operations on tenants table.

Admin operations (like creating new tenants) don't have a tenant context,
so they need special policies that allow operations without tenant_id set.

Revision ID: admin_bypass_rls
Revises: fix_rls_force
Create Date: 2025-11-02 01:20:00.000000

"""

from alembic import op
from sqlalchemy import DDL

# revision identifiers, used by Alembic.
revision = "admin_bypass_rls"
down_revision = "fix_rls_force"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add admin bypass policies for tenants table."""

    # For the tenants table, we need special policies that allow:
    # 1. SELECT without tenant context (for idempotency checks)
    # 2. INSERT without tenant context (for creating new tenants)

    # Drop existing restrictive policies for tenants table
    op.execute("DROP POLICY IF EXISTS tenants_tenant_isolation_select ON tenants")
    op.execute("DROP POLICY IF EXISTS tenants_tenant_isolation_insert ON tenants")

    # Create new SELECT policy: allow if tenant_id matches OR if no tenant context
    # This allows admin operations to query tenants without context
    op.execute(
        DDL("""
        CREATE POLICY tenants_select_policy ON tenants
        FOR SELECT
        USING (
            id::text = current_setting('app.current_tenant_id', TRUE)
            OR current_setting('app.current_tenant_id', TRUE) IS NULL
        )
    """)
    )

    # Create new INSERT policy: allow if id matches tenant context OR if no tenant context
    # This allows admin operations to create tenants without context
    op.execute(
        DDL("""
        CREATE POLICY tenants_insert_policy ON tenants
        FOR INSERT
        WITH CHECK (
            id::text = current_setting('app.current_tenant_id', TRUE)
            OR current_setting('app.current_tenant_id', TRUE) IS NULL
        )
    """)
    )

    # Keep UPDATE and DELETE restrictive (require tenant context)
    # These are not used by admin operations


def downgrade() -> None:
    """Restore original restrictive policies."""

    # Drop admin-friendly policies
    op.execute("DROP POLICY IF EXISTS tenants_select_policy ON tenants")
    op.execute("DROP POLICY IF EXISTS tenants_insert_policy ON tenants")

    # Restore original restrictive policies
    op.execute(
        DDL("""
        CREATE POLICY tenants_tenant_isolation_select ON tenants
        FOR SELECT
        USING (
            id::text = current_setting('app.current_tenant_id', TRUE)
            AND current_setting('app.current_tenant_id', TRUE) IS NOT NULL
        )
    """)
    )

    op.execute(
        DDL("""
        CREATE POLICY tenants_tenant_isolation_insert ON tenants
        FOR INSERT
        WITH CHECK (
            id::text = current_setting('app.current_tenant_id', TRUE)
            AND current_setting('app.current_tenant_id', TRUE) IS NOT NULL
        )
    """)
    )
