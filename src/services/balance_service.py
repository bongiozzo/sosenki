"""Balance service for calculating owner balances and generating balance sheets.

Provides methods for:
- Calculating individual owner balances
- Generating balance sheets for periods
- Carrying forward balances between periods
"""

from decimal import Decimal
from typing import Dict, List, Optional


class BalanceService:
    """Balance calculation and reporting service."""

    def __init__(self):
        """Initialize balance service."""
        pass

    def calculate_balances(
        self,
        period_id: int,
        contributions: Dict[int, Decimal],
        charges: Dict[int, Decimal],
    ) -> Dict[int, Decimal]:
        """Calculate all owner balances for a period.

        Balance = Total Contributions - Total Charges

        Positive balance = owner has credit
        Negative balance = owner owes money

        Args:
            period_id: Service period ID
            contributions: Dict mapping owner_id to total contributions
            charges: Dict mapping owner_id to total charges (allocated expenses + service charges)

        Returns:
            Dict mapping owner_id to balance amount
        """
        all_owners = set(contributions.keys()) | set(charges.keys())

        balances = {}
        for owner_id in all_owners:
            contrib = contributions.get(owner_id, Decimal(0))
            charge = charges.get(owner_id, Decimal(0))
            balances[owner_id] = contrib - charge

        return balances

    def calculate_all_balances(
        self,
        period_id: int,
    ) -> Dict[int, Decimal]:
        """Calculate all owner balances for a period.

        This is a placeholder that should be implemented with database access.

        Balance = Total Contributions - Total Charges

        Args:
            period_id: Service period ID

        Returns:
            Dict mapping owner_id to balance amount
        """
        pass

    def get_owner_balance(
        self,
        period_id: int,
        owner_id: int,
    ) -> Decimal:
        """Get balance for individual owner in period.

        Args:
            period_id: Service period ID
            owner_id: Owner ID

        Returns:
            Owner's balance (positive = credit, negative = owed)
        """
        pass

    def carry_forward_balance(
        self,
        from_period_id: int,
        to_period_id: int,
    ) -> Dict[int, Decimal]:
        """Carry forward balances from one period to the next.

        Negative balances (debts) carry forward as opening charges.
        Positive balances (credits) carry forward as opening contributions.

        Args:
            from_period_id: Closed period ID to carry forward from
            to_period_id: New period ID to carry forward to

        Returns:
            Dict mapping owner_id to carried forward amount
        """
        pass

    def apply_opening_balance(
        self,
        period_id: int,
        opening_balances: Dict[int, Decimal],
    ) -> None:
        """Initialize new period with carry-forward balances.

        Creates opening transactions:
        - Positive balance → opening contribution
        - Negative balance → opening charge

        Args:
            period_id: Target period ID
            opening_balances: Dict mapping owner_id to balance to apply
        """
        pass
