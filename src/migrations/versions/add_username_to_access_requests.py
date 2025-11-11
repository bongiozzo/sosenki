"""Add user_telegram_username to access_requests table.

Revision ID: add_username_to_access_requests
Revises: remove_fk_access_request_user
Create Date: 2025-11-12 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_username_to_access_requests'
down_revision = 'remove_fk_access_request_user'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_telegram_username column to access_requests table
    op.add_column('access_requests', sa.Column('user_telegram_username', sa.String(255), nullable=True))


def downgrade() -> None:
    # Remove user_telegram_username column from access_requests table
    op.drop_column('access_requests', 'user_telegram_username')
