"""Payment ORM model for managing financial transactions."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base, BaseModel


class Payment(Base, BaseModel):
    """Model representing a payment transaction.

    Links owner to account with amount, date, and optional comments.
    """

    __tablename__ = "payments"

    # Foreign keys
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="Owner who made the payment",
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False,
        index=True,
        comment="Account receiving the payment",
    )

    # Payment details
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Payment amount in rubles",
    )
    payment_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Date of payment",
    )
    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional payment comment",
    )

    # Relationships
    owner: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="payments",
        foreign_keys=[owner_id],
    )
    account: Mapped["Account"] = relationship(  # noqa: F821
        "Account",
        back_populates="payments",
        foreign_keys=[account_id],
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_owner_account", "owner_id", "account_id"),
        Index("idx_owner_date", "owner_id", "payment_date"),
        Index("idx_account_date", "account_id", "payment_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<Payment(id={self.id}, owner_id={self.owner_id}, account_id={self.account_id}, "
            f"amount={self.amount}, payment_date={self.payment_date})>"
        )


__all__ = ["Payment"]
