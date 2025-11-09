"""Service charge model - owner-specific charges."""

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base, BaseModel


class ServiceCharge(Base, BaseModel):
    """Service charge for specific owner (not allocated).

    Attributes:
        service_period_id: Reference to service period
        user_id: Owner this charge applies to
        description: Description of the service charge
        amount: Charge amount in currency units
    """

    __tablename__ = "service_charges"

    service_period_id: Mapped[int] = mapped_column(
        ForeignKey("service_periods.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )

    # Relationships
    period: Mapped["ServicePeriod"] = relationship(
        "ServicePeriod", back_populates="charges"
    )
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<ServiceCharge(id={self.id}, user_id={self.user_id}, amount={self.amount})>"
