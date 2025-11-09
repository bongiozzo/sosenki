"""Contribution ledger model - owner payment records."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base, BaseModel


class ContributionLedger(Base, BaseModel):
    """Owner contribution (payment) record.

    Attributes:
        service_period_id: Reference to service period
        user_id: Owner making the contribution
        amount: Contribution amount in currency units (stored as Numeric for precision)
        date: Date of contribution
        comment: Optional notes about the contribution
    """

    __tablename__ = "contribution_ledgers"

    service_period_id: Mapped[int] = mapped_column(
        ForeignKey("service_periods.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    period: Mapped["ServicePeriod"] = relationship(
        "ServicePeriod", back_populates="contributions"
    )
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<ContributionLedger(id={self.id}, user_id={self.user_id}, amount={self.amount})>"
