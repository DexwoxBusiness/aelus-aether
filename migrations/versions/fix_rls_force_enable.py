"""fix_rls_force_enable

Add FORCE ROW LEVEL SECURITY to all RLS-enabled tables.

This is a fix for the previous RLS migration which didn't include FORCE,
causing RLS policies to be ignored for table owners (including test runs).

Revision ID: fix_rls_force
Revises: a3a9c19a1c85
Create Date: 2025-10-26 14:45:00.000000

"""

from alembic import op
from sqlalchemy import DDL

# revision identifiers, used by Alembic.
revision = "fix_rls_force"
down_revision = "a3a9c19a1c85"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add FORCE ROW LEVEL SECURITY to all tenant-scoped tables."""

    tenant_tables = [
        "tenants",
        "users",
        "repositories",
        "code_nodes",
        "code_edges",
        "code_embeddings",
    ]

    for table in tenant_tables:
        # Add FORCE to make RLS apply to table owners/superusers
        # This is CRITICAL for tests which run as the database owner
        op.execute(DDL(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))


def downgrade() -> None:
    """Remove FORCE ROW LEVEL SECURITY (revert to normal RLS)."""

    tenant_tables = [
        "tenants",
        "users",
        "repositories",
        "code_nodes",
        "code_edges",
        "code_embeddings",
    ]

    for table in tenant_tables:
        # Remove FORCE (keeps RLS enabled, just not forced for owners)
        op.execute(DDL(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY"))
