"""Budget item model - allocation strategy definitions."""

from enum import Enum

from sqlalchemy import ForeignKey, String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base, BaseModel


class AllocationStrategy(str, Enum):
    """Expense allocation strategy enumeration."""

    PROPORTIONAL = "PROPORTIONAL"  # Distribute by owner share_weight
    FIXED_FEE = "FIXED_FEE"  # Distribute equally across active properties
    USAGE_BASED = "USAGE_BASED"  # Distribute by consumption (meter readings)
    NONE = "NONE"  # No automatic allocation


class BudgetItem(Base, BaseModel):
    """Budget item defining expense allocation strategy.

    Attributes:
        service_period_id: Reference to service period
        payment_type: Expense category this budget item applies to
        budgeted_cost: Optional budgeted amount for this expense type
        allocation_strategy: How to distribute expenses (PROPORTIONAL, FIXED_FEE, USAGE_BASED, NONE)
    """

    __tablename__ = "budget_items"

    service_period_id: Mapped[int] = mapped_column(
        ForeignKey("service_periods.id"), nullable=False
    )
    payment_type: Mapped[str] = mapped_column(String(100), nullable=False)
    budgeted_cost: Mapped[float | None] = mapped_column(nullable=True)
    allocation_strategy: Mapped[AllocationStrategy] = mapped_column(
        SQLEnum(AllocationStrategy), nullable=False, default=AllocationStrategy.PROPORTIONAL
    )

    # Relationships
    period: Mapped["ServicePeriod"] = relationship(
        "ServicePeriod", back_populates="budget_items"
    )
    expenses: Mapped[list["ExpenseLedger"]] = relationship(
        "ExpenseLedger", back_populates="budget_item"
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<BudgetItem(id={self.id}, type={self.payment_type}, strategy={self.allocation_strategy.value})>"
