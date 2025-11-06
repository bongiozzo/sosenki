"""refactor_user_model_and_add_mini_app_schema

Revision ID: 20030999d2ea
Revises: e2d56fdbda32
Create Date: 2025-11-05 17:05:34.194079
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20030999d2ea'
down_revision = 'e2d56fdbda32'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create User table and rename ClientRequest to AccessRequest."""
    
    # 1. Create users table with unified role model
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.String(length=50), nullable=False, comment='Primary identifier from Telegram'),
        sa.Column('username', sa.String(length=255), nullable=True, comment='Telegram username'),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('is_investor', sa.Boolean(), nullable=False, server_default='0', comment='Can access Invest features (requires is_active=True)'),
        sa.Column('is_administrator', sa.Boolean(), nullable=False, server_default='0', comment='Can approve/reject access requests'),
        sa.Column('is_owner', sa.Boolean(), nullable=False, server_default='0', comment='Can manage system configuration (future)'),
        sa.Column('is_staff', sa.Boolean(), nullable=False, server_default='0', comment='Can view analytics and support users (future)'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1', comment='PRIMARY Mini App access gate - can access Mini App if True'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    op.create_index('idx_telegram_id', 'users', ['telegram_id'], unique=False)
    op.create_index('idx_username', 'users', ['username'], unique=False)
    op.create_index('idx_is_active', 'users', ['is_active'], unique=False)
    op.create_index('idx_investor_active', 'users', ['is_investor', 'is_active'], unique=False)
    
    # 2. Rename client_requests table to access_requests
    op.rename_table('client_requests', 'access_requests')
    
    # 3. Rename columns in access_requests table
    # Note: SQLite doesn't support column rename directly, so we'll recreate the table
    # First, drop existing indexes
    op.drop_index('idx_status', table_name='access_requests')
    op.drop_index('idx_submitted_at', table_name='access_requests')
    
    # Create new access_requests table with correct schema
    op.create_table(
        'access_requests_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_telegram_id', sa.String(length=50), nullable=False, comment='User making the request'),
        sa.Column('request_message', sa.Text(), nullable=False, comment="User's request message"),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='requeststatus', native_enum=False), nullable=False, comment='Current status: pending/approved/rejected'),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False, comment='When request was submitted'),
        sa.Column('responded_by_admin_id', sa.String(length=50), nullable=True, comment='Admin who approved/rejected'),
        sa.Column('response_message', sa.Text(), nullable=True, comment="Admin's response message"),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True, comment='When admin responded'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, comment='Record update timestamp'),
        sa.ForeignKeyConstraint(['user_telegram_id'], ['users.telegram_id']),
        sa.ForeignKeyConstraint(['responded_by_admin_id'], ['users.telegram_id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Copy data from old table to new (mapping old column names to new)
    op.execute("""
        INSERT INTO access_requests_new (id, user_telegram_id, request_message, status, submitted_at, responded_by_admin_id, response_message, responded_at, created_at, updated_at)
        SELECT id, client_telegram_id, request_message, status, submitted_at, admin_telegram_id, admin_response, responded_at, DATETIME('now'), DATETIME('now')
        FROM access_requests
    """)
    
    # Drop old table and rename new one
    op.drop_table('access_requests')
    op.rename_table('access_requests_new', 'access_requests')
    
    # Create indexes on access_requests
    op.create_index('idx_user_status', 'access_requests', ['user_telegram_id', 'status'], unique=False)
    op.create_index('idx_status', 'access_requests', ['status'], unique=False)
    op.create_index('idx_submitted_at', 'access_requests', ['submitted_at'], unique=False)
    op.create_index('idx_responded_by', 'access_requests', ['responded_by_admin_id'], unique=False)


def downgrade() -> None:
    """Revert User table and AccessRequest back to ClientRequest."""
    
    # 1. Drop indexes on access_requests
    op.drop_index('idx_responded_by', table_name='access_requests')
    op.drop_index('idx_submitted_at', table_name='access_requests')
    op.drop_index('idx_status', table_name='access_requests')
    op.drop_index('idx_user_status', table_name='access_requests')
    
    # 2. Recreate old client_requests table
    op.create_table(
        'client_requests_old',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_telegram_id', sa.String(length=50), nullable=False),
        sa.Column('request_message', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='requeststatus', native_enum=False), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('admin_telegram_id', sa.String(length=50), nullable=True),
        sa.Column('admin_response', sa.Text(), nullable=True),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Copy data back
    op.execute("""
        INSERT INTO client_requests_old (id, client_telegram_id, request_message, status, submitted_at, admin_telegram_id, admin_response, responded_at)
        SELECT id, user_telegram_id, request_message, status, submitted_at, responded_by_admin_id, response_message, responded_at
        FROM access_requests
    """)
    
    # Drop new table and rename old one
    op.drop_table('access_requests')
    op.rename_table('client_requests_old', 'client_requests')
    
    # Recreate old indexes
    op.create_index('idx_status', 'client_requests', ['status'], unique=False)
    op.create_index('idx_submitted_at', 'client_requests', ['submitted_at'], unique=False)
    
    # 3. Drop users table
    op.drop_index('idx_investor_active', table_name='users')
    op.drop_index('idx_is_active', table_name='users')
    op.drop_index('idx_username', table_name='users')
    op.drop_index('idx_telegram_id', table_name='users')
    op.drop_table('users')
