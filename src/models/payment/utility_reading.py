"""Utility reading model - meter readings for usage-based billing."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base, BaseModel


class UtilityReading(Base, BaseModel):
    """Meter reading for utility consumption tracking.

    Attributes:
        service_period_id: Reference to service period
        meter_name: Name/identifier of meter (e.g., "Water Meter A", "Electric Meter")
        meter_start_reading: Starting meter reading at period start
        meter_end_reading: Ending meter reading at period end
        calculated_total_cost: Total cost for consumption during period
        unit: Unit of measurement (kWh, m³, etc.)
        description: Optional notes about the reading
    """

    __tablename__ = "utility_readings"

    service_period_id: Mapped[int] = mapped_column(
        ForeignKey("service_periods.id"), nullable=False
    )
    meter_name: Mapped[str] = mapped_column(String(255), nullable=False)
    meter_start_reading: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=3), nullable=False
    )
    meter_end_reading: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=3), nullable=False
    )
    calculated_total_cost: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    period: Mapped["ServicePeriod"] = relationship(
        "ServicePeriod", back_populates="readings"
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<UtilityReading(id={self.id}, meter={self.meter_name}, cost={self.calculated_total_cost})>"
