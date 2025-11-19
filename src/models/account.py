"""Account ORM model for managing payment accounts."""

from enum import Enum

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base, BaseModel


class AccountType(str, Enum):
    """Account classification."""

    USER = "user"
    """Personal account linked to a User (1:1 relationship)."""

    ORGANIZATION = "organization"
    """Shared organization/fund account (no User link)."""


class Account(Base, BaseModel):
    """Model representing a payment account.

    Polymorphic account supporting both user personal accounts and shared
    organization accounts. All transactions flow between accounts (from_account → to_account).

    Account types:
    - USER: Personal account for a community member (1:1 with User)
    - ORGANIZATION: Shared fund account (e.g., "Взносы", "Reserve")
    """

    __tablename__ = "accounts"

    # Account identity
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Account name (e.g., 'Радионов', 'Взносы', 'Reserve')",
    )

    # Account classification
    account_type: Mapped[AccountType] = mapped_column(
        String(50),
        nullable=False,
        default=AccountType.ORGANIZATION,
        comment="Account type: 'user' for personal, 'organization' for shared fund",
    )

    # User link (only for account_type='user')
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
        comment="FK to User if account_type='user' (1:1 relationship)",
    )

    # Relationships
    user: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[user_id],
        back_populates="account",
        uselist=False,
    )

    from_transactions: Mapped[list["Transaction"]] = relationship(  # noqa: F821
        "Transaction",
        back_populates="from_account",
        foreign_keys="Transaction.from_account_id",
        cascade="all, delete-orphan",
    )

    to_transactions: Mapped[list["Transaction"]] = relationship(  # noqa: F821
        "Transaction",
        back_populates="to_account",
        foreign_keys="Transaction.to_account_id",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_account_name", "name"),
        Index("idx_account_type", "account_type"),
        Index("idx_account_user", "user_id", "account_type", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, name={self.name!r}, type={self.account_type})>"


__all__ = ["Account", "AccountType"]
