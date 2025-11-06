"""aaet29_soft_delete_tenants

Add deleted_at column to tenants table for soft delete (AAET-29).

Revision ID: aaet29_soft_delete
Revises: admin_bypass_rls
Create Date: 2025-11-05 00:40:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "aaet29_soft_delete"
down_revision = "admin_bypass_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add deleted_at column to tenants for soft delete."""
    op.add_column("tenants", sa.Column("deleted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove deleted_at column."""
    op.drop_column("tenants", "deleted_at")
