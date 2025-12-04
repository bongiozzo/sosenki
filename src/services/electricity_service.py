"""Service for electricity billing calculations and distribution."""

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.bill import Bill, BillType
from src.models.property import Property
from src.models.service_period import ServicePeriod
from src.models.user import User

logger = logging.getLogger(__name__)


class OwnerShare(NamedTuple):
    """Represents an owner's share in distributed costs."""

    user_id: int
    user_name: str
    total_share_weight: Decimal
    calculated_bill_amount: Decimal


class ElectricityService:
    """Service for electricity billing calculations and cost distribution."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def calculate_total_electricity(
        self,
        electricity_start: Decimal,
        electricity_end: Decimal,
        electricity_multiplier: Decimal,
        electricity_rate: Decimal,
        electricity_losses: Decimal,
    ) -> Decimal:
        """Calculate total electricity cost.

        Formula: (end - start) × multiplier × rate × (1 + losses)

        Args:
            electricity_start: Starting meter reading (kWh)
            electricity_end: Ending meter reading (kWh)
            electricity_multiplier: Consumption multiplier
            electricity_rate: Rate per kWh
            electricity_losses: Transmission losses ratio (e.g., 0.2 for 20%)

        Returns:
            Total electricity cost as Decimal (rounded to 2 decimal places)

        Raises:
            ValueError: If electricity_end <= electricity_start or any negative values
        """
        if electricity_end <= electricity_start:
            raise ValueError("Electricity end reading must be greater than start reading")
        if electricity_start < 0 or electricity_end < 0:
            raise ValueError("Electricity readings cannot be negative")
        if electricity_multiplier <= 0 or electricity_rate <= 0:
            raise ValueError("Multiplier and rate must be positive")
        if electricity_losses < 0:
            raise ValueError("Losses cannot be negative")

        consumption = electricity_end - electricity_start
        total = (
            consumption
            * electricity_multiplier
            * electricity_rate
            * (Decimal(1) + electricity_losses)
        )

        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def get_electricity_bills_for_period(
        self,
        service_period_id: int,
    ) -> Decimal:
        """Query sum of all existing ELECTRICITY bills for a service period.

        Args:
            service_period_id: Service period ID to query

        Returns:
            Sum of all ELECTRICITY bill amounts for the period (or 0 if none exist)
        """
        result = self.db.execute(
            select(func.sum(Bill.bill_amount)).where(
                (Bill.service_period_id == service_period_id)
                & (Bill.bill_type == BillType.ELECTRICITY)
            )
        ).scalar()

        return result or Decimal(0)

    def calculate_owner_shares(
        self,
        service_period: ServicePeriod,
    ) -> dict[int, Decimal]:
        """Aggregate properties by owner with sum of share_weight.

        Args:
            service_period: Service period to query properties for

        Returns:
            Dict mapping user_id → total_share_weight for all property owners
        """
        # Query all active properties and group by owner
        stmt = (
            select(
                Property.owner_id,
                func.sum(Property.share_weight).label("total_weight"),
            )
            .where(
                Property.is_active == True  # noqa: E712
            )
            .group_by(Property.owner_id)
        )

        results = self.db.execute(stmt).all()

        owner_shares = {}
        for owner_id, total_weight in results:
            if total_weight is not None:
                owner_shares[owner_id] = Decimal(str(total_weight))

        return owner_shares

    def distribute_shared_costs(
        self,
        total_shared_cost: Decimal,
        service_period: ServicePeriod,
    ) -> list[OwnerShare]:
        """Calculate proportional distribution of shared electricity costs.

        Distribution formula: user_share = total × (user_weight_sum / total_weight_sum)

        Args:
            total_shared_cost: Total shared electricity cost to distribute
            service_period: Service period for context

        Returns:
            List of OwnerShare tuples with calculated amounts per owner
        """
        if total_shared_cost < 0:
            raise ValueError("Total shared cost cannot be negative")

        # Get owner shares (weight aggregation)
        owner_shares = self.calculate_owner_shares(service_period)

        if not owner_shares:
            logger.warning("No active properties found for distribution")
            return []

        # Calculate total weight sum
        total_weight_sum = sum(owner_shares.values())

        if total_weight_sum == 0:
            logger.warning("Total weight sum is zero, cannot distribute")
            return []

        # Calculate per-owner shares
        result = []
        for owner_id, owner_weight in owner_shares.items():
            # Get user name
            user = self.db.execute(select(User).where(User.id == owner_id)).scalar_one_or_none()
            if not user:
                logger.warning("User %d not found for owner_id", owner_id)
                continue

            # Calculate proportional share
            user_share_amount = (total_shared_cost * (owner_weight / total_weight_sum)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            result.append(
                OwnerShare(
                    user_id=owner_id,
                    user_name=user.name or f"User {owner_id}",
                    total_share_weight=owner_weight,
                    calculated_bill_amount=user_share_amount,
                )
            )

        return result

    def get_previous_service_period(self) -> ServicePeriod | None:
        """Get the most recent service period before current date.

        Used for fetching default electricity parameters.

        Returns:
            Previous service period or None if not found
        """
        stmt = (
            select(ServicePeriod)
            .where(ServicePeriod.status == "open")
            .order_by(ServicePeriod.start_date.desc())
            .limit(1)
        )

        return self.db.execute(stmt).scalar_one_or_none()
