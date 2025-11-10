"""make telegram_id nullable and name unique

Revision ID: d60e7a4d6899
Revises: c41773ae4774
Create Date: 2025-11-10 10:00:22.042925
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd60e7a4d6899'
down_revision = 'c41773ae4774'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to properties
    op.add_column('properties', sa.Column('is_for_tenant', sa.Boolean(), nullable=False, server_default='0', comment='Whether property is for tenant'))
    op.add_column('properties', sa.Column('photo_link', sa.String(length=500), nullable=True, comment="URL to property's photo gallery"))
    op.add_column('properties', sa.Column('sale_price', sa.Numeric(precision=10, scale=2), nullable=True, comment='Selling price of the property'))
    
    # Use batch mode for SQLite to handle complex operations
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Drop old columns
        batch_op.drop_column('first_name')
        batch_op.drop_column('last_name')
        
        # Recreate telegram_id as nullable (drop and re-add without index)
        batch_op.drop_column('telegram_id')
        batch_op.add_column(sa.Column('telegram_id', sa.String(length=50), nullable=True, comment='Primary identifier from Telegram (nullable until user becomes active)'))
        
        # Add new columns
        batch_op.add_column(sa.Column('name', sa.String(length=255), nullable=False, comment='Full name (first and last name combined) - unique identifier'))
        batch_op.add_column(sa.Column('is_stakeholder', sa.Boolean(), nullable=False, server_default='0', comment="Stakeholder status from Google Sheet 'Доля' column"))
        
        # Create unique index for name
        batch_op.create_index('idx_name_unique', ['name'], unique=True)
    
    # Create partial unique index for telegram_id (only when not null) - do this after batch
    # Use raw SQL for SQLite WHERE clause
    op.execute('CREATE UNIQUE INDEX idx_telegram_id_unique ON users (telegram_id) WHERE telegram_id IS NOT NULL')


def downgrade() -> None:
    op.drop_index('idx_telegram_id_unique', table_name='users')
    
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_stakeholder')
        batch_op.drop_column('name')
        batch_op.drop_column('telegram_id')
        batch_op.add_column(sa.Column('telegram_id', sa.VARCHAR(length=50), nullable=False, unique=True))
        batch_op.add_column(sa.Column('first_name', sa.VARCHAR(length=255), nullable=True))
        batch_op.add_column(sa.Column('last_name', sa.VARCHAR(length=255), nullable=True))
    
    op.drop_column('properties', 'sale_price')
    op.drop_column('properties', 'photo_link')
    op.drop_column('properties', 'is_for_tenant')
