"""Initial schema: Create all tables for MVP.

This is the only migration file - represents the current final schema for MVP.
Since we're not in production and backward compatibility is not required,
this is a fresh start reflecting all current models in src/models/.

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-11-12 13:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.String(length=50), nullable=True),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_investor', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_administrator', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_owner', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_staff', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_stakeholder', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_tenant', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.Index('ix_users_is_active', 'is_active'),
        sa.Index('ix_users_telegram_id', 'telegram_id'),
        sa.Index('ix_users_username', 'username'),
        sa.Index('ix_users_is_tenant', 'is_tenant'),
    )

    # Create properties table
    op.create_table(
        'properties',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('property_name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=100), nullable=True),
        sa.Column('share_weight', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('is_ready', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_for_tenant', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('photo_link', sa.String(length=500), nullable=True),
        sa.Column('sale_price', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_properties_owner_id', 'owner_id'),
    )

    # Create access_requests table
    op.create_table(
        'access_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_telegram_id', sa.String(length=50), nullable=False, index=True),
        sa.Column('user_telegram_username', sa.String(length=255), nullable=True),
        sa.Column('request_message', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', native_enum=False), nullable=False, server_default='pending', index=True),
        sa.Column('admin_telegram_id', sa.String(length=50), nullable=True, index=True),
        sa.Column('admin_response', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['admin_telegram_id'], ['users.telegram_id'], ),
        sa.Index('idx_user_status', 'user_telegram_id', 'status'),
        sa.Index('idx_status', 'status'),
    )


def downgrade() -> None:
    # For MVP with no backward compatibility requirement, downgrade is not implemented.
    # To reset: use `make db-reset` to drop and recreate schema fresh.
    pass
