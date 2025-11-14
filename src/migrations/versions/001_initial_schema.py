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

    # Create service_periods table
    op.create_table(
        'service_periods',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('period_key', sa.String(length=10), nullable=False, unique=True),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('is_closed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create utility_readings table
    op.create_table(
        'utility_readings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_period_id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('meter_type', sa.String(length=50), nullable=False),
        sa.Column('reading_value', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column('submission_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ),
        sa.ForeignKeyConstraint(['service_period_id'], ['service_periods.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_utility_readings_property_id', 'property_id'),
        sa.Index('ix_utility_readings_service_period_id', 'service_period_id'),
    )

    # Create budget_items table
    op.create_table(
        'budget_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_period_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('budgeted_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('spent_amount', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['service_period_id'], ['service_periods.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_budget_items_service_period_id', 'service_period_id'),
    )

    # Create expense_ledgers table
    op.create_table(
        'expense_ledgers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_period_id', sa.Integer(), nullable=False),
        sa.Column('budget_item_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('submitted_by_user_id', sa.Integer(), nullable=False),
        sa.Column('submission_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['budget_item_id'], ['budget_items.id'], ),
        sa.ForeignKeyConstraint(['service_period_id'], ['service_periods.id'], ),
        sa.ForeignKeyConstraint(['submitted_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_expense_ledgers_budget_item_id', 'budget_item_id'),
        sa.Index('ix_expense_ledgers_service_period_id', 'service_period_id'),
        sa.Index('ix_expense_ledgers_submitted_by_user_id', 'submitted_by_user_id'),
    )

    # Create contribution_ledgers table
    op.create_table(
        'contribution_ledgers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_period_id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('share_of_total', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('contribution_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ),
        sa.ForeignKeyConstraint(['service_period_id'], ['service_periods.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_contribution_ledgers_property_id', 'property_id'),
        sa.Index('ix_contribution_ledgers_service_period_id', 'service_period_id'),
    )

    # Create service_charges table
    op.create_table(
        'service_charges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_period_id', sa.Integer(), nullable=False),
        sa.Column('property_id', sa.Integer(), nullable=False),
        sa.Column('meter_type', sa.String(length=50), nullable=False),
        sa.Column('consumption', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column('rate', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('charge_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ),
        sa.ForeignKeyConstraint(['service_period_id'], ['service_periods.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_service_charges_property_id', 'property_id'),
        sa.Index('ix_service_charges_service_period_id', 'service_period_id'),
    )


def downgrade() -> None:
    # For MVP with no backward compatibility requirement, downgrade is not implemented.
    # To reset: use `make db-reset` to drop and recreate schema fresh.
    pass
