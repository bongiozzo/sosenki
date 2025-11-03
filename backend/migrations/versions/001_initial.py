"""Initial migration - create users, telegram_user_candidates, and admin_actions tables.

Revision ID: 001
Revises:
Create Date: 2025-11-03 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create sosenki_user table
    op.create_table(
        "sosenki_user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=True),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("roles", sa.JSON(), nullable=False, server_default='["User"]'),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("bio", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_sosenki_user_username"),
        sa.UniqueConstraint("telegram_id", name="uq_sosenki_user_telegram_id"),
    )

    # Create telegram_user_candidate table
    op.create_table(
        "telegram_user_candidate",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("first_name", sa.String(), nullable=True),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id", name="uq_telegram_user_candidate_telegram_id"),
    )

    # Create admin_action table
    op.create_table(
        "admin_action",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["telegram_user_candidate.id"],
        ),
    )

    # Create indexes
    op.create_index(op.f("ix_admin_action_admin_id"), "admin_action", ["admin_id"], unique=False)
    op.create_index(
        op.f("ix_admin_action_request_id"), "admin_action", ["request_id"], unique=False
    )
    op.create_index(
        op.f("ix_sosenki_user_telegram_id"), "sosenki_user", ["telegram_id"], unique=False
    )
    op.create_index(
        op.f("ix_telegram_user_candidate_telegram_id"),
        "telegram_user_candidate",
        ["telegram_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index(
        op.f("ix_telegram_user_candidate_telegram_id"), table_name="telegram_user_candidate"
    )
    op.drop_index(op.f("ix_sosenki_user_telegram_id"), table_name="sosenki_user")
    op.drop_index(op.f("ix_admin_action_request_id"), table_name="admin_action")
    op.drop_index(op.f("ix_admin_action_admin_id"), table_name="admin_action")
    op.drop_table("admin_action")
    op.drop_table("telegram_user_candidate")
    op.drop_table("sosenki_user")
