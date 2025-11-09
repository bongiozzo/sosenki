"""Merge payment models and schema updates

Revision ID: 3bab1f45f28a
Revises: 001_create_payment_models, 20030999d2ea
Create Date: 2025-11-09 19:45:54.213410
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3bab1f45f28a'
down_revision = ('001_create_payment_models', '20030999d2ea')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
