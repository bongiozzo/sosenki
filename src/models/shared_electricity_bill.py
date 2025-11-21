"""
Shared electricity bill model for common area (communal) electricity charges.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .user import Base


class SharedElectricityBill(Base):
    """
    Model representing a shared electricity bill for common area charges.

    Attributes:
        id: Primary key
        service_period_id: Foreign key to service_periods
        user_id: Foreign key to users
        bill_amount: Bill amount in rubles (numeric)
        comment: Optional comment about the bill
        created_at: Record creation timestamp
        updated_at: Record update timestamp
    """

    __tablename__ = "shared_electricity_bills"

    id = Column(Integer, primary_key=True, index=True)
    service_period_id = Column(
        Integer, ForeignKey("service_periods.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bill_amount = Column(Numeric(10, 2), nullable=False, doc="Bill amount in rubles")
    comment = Column(
        String(500), nullable=True, default=None, doc="Optional comment about the bill"
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    service_period = relationship("ServicePeriod", back_populates="shared_bills")
    user = relationship("User", back_populates="shared_bills")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("service_period_id", "user_id", name="uq_shared_bill_period_user"),
        Index("idx_shared_bill_period_user", "service_period_id", "user_id"),
    )

    def __repr__(self):
        return (
            f"<SharedElectricityBill(id={self.id}, "
            f"service_period_id={self.service_period_id}, "
            f"user_id={self.user_id}, "
            f"bill_amount={self.bill_amount})>"
        )
