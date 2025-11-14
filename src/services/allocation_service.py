"""Allocation service for distributing expenses across owners using different strategies.

Supports allocation strategies:
- PROPORTIONAL: Distribute by owner share weight
- FIXED_FEE: Distribute equally across active properties
- USAGE_BASED: Distribute by consumption (meter readings)
- NONE: No automatic allocation
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Dict


class AllocationService:
    """Expense allocation engine with multiple strategies."""

    def __init__(self):
        """Initialize allocation service."""
        pass

    def distribute_with_remainder(
        self,
        total_amount: Decimal,
        shares: Dict[int, Decimal],
    ) -> Dict[int, Decimal]:
        """Distribute amount by shares, allocating remainder to largest share holders.

        Ensures: sum(result) == total_amount (zero money loss/creation)

        Algorithm:
        1. Calculate per-unit allocation: total / sum(shares)
        2. Allocate: amount_per_owner = per_unit * share_weight (rounded down)
        3. Calculate remainder
        4. Sort owners by remainder descending
        5. Distribute remainder (1 cent per owner) to largest remainder holders

        Args:
            total_amount: Total to distribute (Decimal)
            shares: Dict mapping owner_id to share weight (Decimal)

        Returns:
            Dict mapping owner_id to allocated amount (Decimal)
        """
        if not shares:
            return {}

        # Convert all to Decimal for precision
        total = Decimal(str(total_amount))
        share_dict = {k: Decimal(str(v)) for k, v in shares.items()}

        total_shares = sum(share_dict.values())
        if total_shares == 0:
            return {k: Decimal(0) for k in share_dict.keys()}

        # Calculate per-unit allocation
        per_unit = total / total_shares

        # Allocate with truncation to 2 decimal places
        allocations = {}
        allocated_total = Decimal(0)

        for owner_id, share_weight in share_dict.items():
            # Calculate allocation (truncate to 2 decimals)
            allocated = (per_unit * share_weight).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            allocations[owner_id] = allocated
            allocated_total += allocated

        # Calculate exact remainder to distribute
        remainder = total - allocated_total

        if remainder > 0:
            # Convert remainder to cents (integer)
            remainder_cents = int(round(remainder * 100))

            # Sort by share weight descending (largest shares get remainder first)
            sorted_owners = sorted(share_dict.items(), key=lambda x: x[1], reverse=True)

            for i in range(min(remainder_cents, len(sorted_owners))):
                owner_id = sorted_owners[i][0]
                allocations[owner_id] += Decimal("0.01")

        return allocations

    def allocate_proportional(
        self,
        total_amount: Decimal,
        property_shares: Dict[int, Decimal],
    ) -> Dict[int, Decimal]:
        """Allocate by proportional ownership.

        Args:
            total_amount: Total expense to allocate
            property_shares: Dict mapping owner_id to share weight

        Returns:
            Dict mapping owner_id to allocated amount
        """
        return self.distribute_with_remainder(total_amount, property_shares)

    def allocate_fixed_fee(
        self,
        total_amount: Decimal,
        active_owner_count: int,
    ) -> Dict[int, Decimal]:
        """Allocate equally across active property owners.

        Args:
            total_amount: Total expense to allocate
            active_owner_count: Number of active properties

        Returns:
            Dict mapping to allocated amount per owner
        """
        if active_owner_count <= 0:
            return {}

        per_owner = (total_amount / Decimal(str(active_owner_count))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Calculate remainder
        remainder = total_amount - (per_owner * Decimal(str(active_owner_count)))

        # Allocate remainder cents to first N owners
        result = {}
        remainder_cents = int((remainder * 100).quantize(Decimal("1")))

        for i in range(active_owner_count):
            amount = per_owner
            if i < remainder_cents:
                amount += Decimal("0.01")
            result[i] = amount

        return result

    def calculate_consumption(
        self,
        start_reading: Decimal,
        end_reading: Decimal,
    ) -> Decimal:
        """Calculate consumption from meter readings.

        Args:
            start_reading: Starting meter reading
            end_reading: Ending meter reading

        Returns:
            Consumption amount (end - start)
        """
        return Decimal(str(end_reading)) - Decimal(str(start_reading))

    def allocate_usage_based(
        self,
        total_cost: Decimal,
        consumption_by_owner: Dict[int, Decimal],
    ) -> Dict[int, Decimal]:
        """Allocate by usage consumption.

        Args:
            total_cost: Total cost to allocate
            consumption_by_owner: Dict mapping owner_id to consumption amount

        Returns:
            Dict mapping owner_id to allocated cost
        """
        total_consumption = sum(consumption_by_owner.values())
        if total_consumption == 0:
            return {k: Decimal(0) for k in consumption_by_owner.keys()}

        # Convert to shares (consumption as weight)
        return self.distribute_with_remainder(total_cost, consumption_by_owner)

    def allocate_expenses(
        self,
        expense_amount: Decimal,
        allocation_strategy: str,
        owner_shares: Dict[int, Decimal] = None,
        owner_consumption: Dict[int, Decimal] = None,
    ) -> Dict[int, Decimal]:
        """Allocate expense using specified strategy.

        Orchestrates allocation based on strategy type.

        Args:
            expense_amount: Total expense to allocate
            allocation_strategy: Strategy name (PROPORTIONAL, FIXED_FEE, USAGE_BASED, NONE)
            owner_shares: Dict for PROPORTIONAL/FIXED_FEE (owner_id -> weight)
            owner_consumption: Dict for USAGE_BASED (owner_id -> consumption)

        Returns:
            Dict mapping owner_id to allocated amount

        Raises:
            ValueError: If strategy invalid or required data missing
        """
        if allocation_strategy == "PROPORTIONAL":
            if not owner_shares:
                raise ValueError("owner_shares required for PROPORTIONAL allocation")
            return self.allocate_proportional(expense_amount, owner_shares)

        elif allocation_strategy == "FIXED_FEE":
            if not owner_shares:
                raise ValueError("owner_shares required for FIXED_FEE allocation")
            return self.allocate_fixed_fee(expense_amount, len(owner_shares))

        elif allocation_strategy == "USAGE_BASED":
            if not owner_consumption:
                raise ValueError("owner_consumption required for USAGE_BASED allocation")
            return self.allocate_usage_based(expense_amount, owner_consumption)

        elif allocation_strategy == "NONE":
            # No allocation - return zeros
            if owner_shares:
                return {k: Decimal(0) for k in owner_shares.keys()}
            elif owner_consumption:
                return {k: Decimal(0) for k in owner_consumption.keys()}
            else:
                return {}

        else:
            raise ValueError(f"Unknown allocation strategy: {allocation_strategy}")
