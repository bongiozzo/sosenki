"""Service period model - discrete accounting periods (OPEN/CLOSED state machine)."""

from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, String, Table, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base, BaseModel


class PeriodStatus(str, Enum):
    """Service period status enumeration."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ServicePeriod(Base, BaseModel):
    """Discrete accounting period for financial transactions.

    Attributes:
        name: Human-readable period identifier (e.g., "Nov 2025")
        start_date: Period start date (inclusive)
        end_date: Period end date (inclusive)
        status: OPEN (accepting transactions) or CLOSED (finalized)
        description: Optional period notes
    """

    __tablename__ = "service_periods"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    start_date: Mapped[date] = mapped_column(nullable=False)
    end_date: Mapped[date] = mapped_column(nullable=False)
    status: Mapped[PeriodStatus] = mapped_column(
        SQLEnum(PeriodStatus), nullable=False, default=PeriodStatus.OPEN
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    contributions: Mapped[list["ContributionLedger"]] = relationship(
        "ContributionLedger",
        back_populates="period",
        cascade="all, delete-orphan",
    )
    expenses: Mapped[list["ExpenseLedger"]] = relationship(
        "ExpenseLedger",
        back_populates="period",
        cascade="all, delete-orphan",
    )
    budget_items: Mapped[list["BudgetItem"]] = relationship(
        "BudgetItem",
        back_populates="period",
        cascade="all, delete-orphan",
    )
    readings: Mapped[list["UtilityReading"]] = relationship(
        "UtilityReading",
        back_populates="period",
        cascade="all, delete-orphan",
    )
    charges: Mapped[list["ServiceCharge"]] = relationship(
        "ServiceCharge",
        back_populates="period",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<ServicePeriod(id={self.id}, name='{self.name}', status={self.status.value})>"
