"""Expense ledger model - community expense records with payer attribution."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base, BaseModel


class ExpenseLedger(Base, BaseModel):
    """Community expense record with payer attribution.

    Attributes:
        service_period_id: Reference to service period
        paid_by_user_id: User who paid the expense (credited for reimbursement)
        amount: Expense amount in currency units
        payment_type: Category of expense (utilities, security, repairs, etc.)
        date: Date of expense
        vendor: Vendor or service provider name
        description: Detailed description of the expense
        budget_item_id: Reference to budget item for allocation strategy (optional)
    """

    __tablename__ = "expense_ledgers"

    service_period_id: Mapped[int] = mapped_column(
        ForeignKey("service_periods.id"), nullable=False
    )
    paid_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )
    payment_type: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    budget_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("budget_items.id"), nullable=True
    )

    # Relationships
    period: Mapped["ServicePeriod"] = relationship(
        "ServicePeriod", back_populates="expenses"
    )
    paid_by_user: Mapped["User"] = relationship("User")
    budget_item: Mapped["BudgetItem | None"] = relationship(
        "BudgetItem", back_populates="expenses"
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<ExpenseLedger(id={self.id}, amount={self.amount}, type={self.payment_type})>"
