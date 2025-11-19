"""Service period ORM model for grouping transactions into billing cycles."""

from datetime import date
from enum import Enum

from sqlalchemy import Date
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base, BaseModel


class PeriodStatus(str, Enum):
    """Status of a service/billing period."""

    OPEN = "open"
    CLOSED = "closed"


class ServicePeriod(Base, BaseModel):
    """Model representing an accounting/billing period.

    Groups transactions into periods for bill calculation and budget reporting.
    """

    __tablename__ = "service_periods"

    # Period identification
    name: Mapped[str] = mapped_column(
        nullable=False,
        unique=True,
        index=True,
        comment="Period identifier (e.g., '2024-Q4', '2025-Jan')",
    )
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Period start date",
    )
    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Period end date",
    )
    status: Mapped[PeriodStatus] = mapped_column(
        SQLEnum(PeriodStatus),
        nullable=False,
        default=PeriodStatus.OPEN,
        comment="Period status (open for transactions, closed for calculation)",
    )
    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(  # noqa: F821
        "Transaction",
        back_populates="service_period",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ServicePeriod(id={self.id}, name={self.name}, status={self.status})>"


__all__ = ["ServicePeriod", "PeriodStatus"]
