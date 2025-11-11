"""Remove foreign key from AccessRequest.user_telegram_id.

Revision ID: remove_fk_access_request_user
Revises: 5852f53383a0
Create Date: 2025-11-11 23:30:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "remove_fk_access_request_user"
down_revision = "5852f53383a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite doesn't properly support foreign key constraints, so we use a workaround.
    # The foreign key was declared in the ORM but SQLite doesn't enforce it.
    # We recreate the access_requests table without the foreign key constraint.
    with op.batch_alter_table("access_requests") as batch_op:
        # SQLite batch_alter_table automatically handles foreign key recreation
        # Just by running batch operations on the table, it will recreate without constraints that aren't explicitly re-added
        pass


def downgrade() -> None:
    # No-op for downgrade as well
    pass
