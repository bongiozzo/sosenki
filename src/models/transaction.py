"""Transaction ORM model for unified account-to-account transactions."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base, BaseModel


class Transaction(Base, BaseModel):
    """Model representing unified account-to-account transactions.

    All transactions flow between accounts:
    - User contribution: User account → Community account
    - Expense reimbursement: Community account → User account
    - Community transfer: Community account → Community account
    - Salary/charge: Community account → User account

    Polymorphic structure supports all transaction types through flexible
    from/to account relationships.
    """

    __tablename__ = "transactions"

    # Foreign keys (required)
    from_account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False,
        index=True,
        comment="Source account",
    )
    to_account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False,
        index=True,
        comment="Destination account",
    )
    service_period_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_periods.id"),
        nullable=True,
        index=True,
        comment="Associated service period",
    )

    # Transaction details
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Transaction amount in rubles",
    )
    transaction_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Date of transaction",
    )
    description: Mapped[str | None] = mapped_column(
        nullable=True,
        comment="Optional transaction description",
    )

    # Relationships
    from_account: Mapped["Account"] = relationship(  # noqa: F821
        "Account",
        back_populates="from_transactions",
        foreign_keys=[from_account_id],
    )
    to_account: Mapped["Account"] = relationship(  # noqa: F821
        "Account",
        back_populates="to_transactions",
        foreign_keys=[to_account_id],
    )
    service_period: Mapped["ServicePeriod | None"] = relationship(  # noqa: F821
        "ServicePeriod",
        back_populates="transactions",
        foreign_keys=[service_period_id],
    )
    budget_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("budget_items.id"),
        nullable=True,
        index=True,
        comment="Optional reference to budget item for expense categorization",
    )
    budget_item: Mapped["BudgetItem | None"] = relationship(  # noqa: F821
        "BudgetItem",
        foreign_keys=[budget_item_id],
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_transaction_from_account", "from_account_id"),
        Index("idx_transaction_to_account", "to_account_id"),
        Index("idx_transaction_from_to", "from_account_id", "to_account_id"),
        Index("idx_transaction_period", "service_period_id"),
        Index("idx_transaction_date", "transaction_date"),
        Index("idx_transaction_budget_item", "budget_item_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, from_account_id={self.from_account_id}, "
            f"to_account_id={self.to_account_id}, amount={self.amount}, "
            f"date={self.transaction_date})>"
        )


__all__ = ["Transaction"]
