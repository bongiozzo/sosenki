"""Account ORM model for managing payment accounts."""

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base, BaseModel


class Account(Base, BaseModel):
    """Model representing a payment account.

    An account is a logical grouping for financial transactions.
    Account names are configured in seeding.json and can be extracted
    from payment data or set as defaults.
    """

    __tablename__ = "accounts"

    # Account name
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Account name",
    )

    # Relationships
    payments: Mapped[list["Payment"]] = relationship(  # noqa: F821
        "Payment",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (Index("idx_account_name", "name", unique=True),)

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, name={self.name!r})>"


__all__ = ["Account"]
