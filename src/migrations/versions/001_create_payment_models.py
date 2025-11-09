"""Create payment models.

Revision ID: 001_create_payment_models
Revises: None
Create Date: 2025-11-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_create_payment_models'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create payment tables."""
    # Create service_periods table
    op.create_table(
        'service_periods',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('status', sa.Enum('OPEN', 'CLOSED', name='periodstatus'), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # Create contribution_ledgers table
    op.create_table(
        'contribution_ledgers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('service_period_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('comment', sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(['service_period_id'], ['service_periods.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_contribution_ledgers_service_period_id_user_id', 'contribution_ledgers', ['service_period_id', 'user_id'])

    # Create budget_items table
    op.create_table(
        'budget_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('service_period_id', sa.Integer(), nullable=False),
        sa.Column('payment_type', sa.String(100), nullable=False),
        sa.Column('budgeted_cost', sa.Float(), nullable=True),
        sa.Column('allocation_strategy', sa.Enum('PROPORTIONAL', 'FIXED_FEE', 'USAGE_BASED', 'NONE', name='allocationstrategy'), nullable=False),
        sa.ForeignKeyConstraint(['service_period_id'], ['service_periods.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('service_period_id', 'payment_type'),
    )

    # Create expense_ledgers table
    op.create_table(
        'expense_ledgers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('service_period_id', sa.Integer(), nullable=False),
        sa.Column('paid_by_user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('payment_type', sa.String(100), nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('vendor', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('budget_item_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['budget_item_id'], ['budget_items.id'], ),
        sa.ForeignKeyConstraint(['paid_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['service_period_id'], ['service_periods.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_expense_ledgers_service_period_id_paid_by_user_id', 'expense_ledgers', ['service_period_id', 'paid_by_user_id'])
    op.create_index('ix_expense_ledgers_service_period_id_payment_type', 'expense_ledgers', ['service_period_id', 'payment_type'])

    # Create utility_readings table
    op.create_table(
        'utility_readings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('service_period_id', sa.Integer(), nullable=False),
        sa.Column('meter_name', sa.String(255), nullable=False),
        sa.Column('meter_start_reading', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column('meter_end_reading', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column('calculated_total_cost', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['service_period_id'], ['service_periods.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_utility_readings_service_period_id_meter_name', 'utility_readings', ['service_period_id', 'meter_name'])

    # Create service_charges table
    op.create_table(
        'service_charges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('service_period_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(255), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['service_period_id'], ['service_periods.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_service_charges_service_period_id_user_id', 'service_charges', ['service_period_id', 'user_id'])


def downgrade() -> None:
    """Drop payment tables."""
    op.drop_table('service_charges')
    op.drop_table('utility_readings')
    op.drop_table('expense_ledgers')
    op.drop_table('budget_items')
    op.drop_table('contribution_ledgers')
    op.drop_table('service_periods')
