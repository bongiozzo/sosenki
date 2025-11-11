"""Make share_weight nullable in properties

Revision ID: 5852f53383a0
Revises: d60e7a4d6899
Create Date: 2025-11-11 17:22:39.218871
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '5852f53383a0'
down_revision = 'd60e7a4d6899'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Make share_weight nullable in properties table.

    SQLite doesn't support ALTER COLUMN, so we need to recreate the table.
    This is automatically handled by SQLAlchemy's batch_alter_table context manager.
    """
    with op.batch_alter_table('properties', schema=None) as batch_op:
        batch_op.alter_column('share_weight',
                   existing_type=sa.NUMERIC(precision=10, scale=2),
                   nullable=True)


def downgrade() -> None:
    """Revert share_weight to NOT NULL."""
    with op.batch_alter_table('properties', schema=None) as batch_op:
        batch_op.alter_column('share_weight',
                   existing_type=sa.NUMERIC(precision=10, scale=2),
                   nullable=False)
