"""Balance service for calculating owner balances and generating balance sheets.

Provides methods for:
- Calculating individual owner balances
- Generating balance sheets for periods
- Carrying forward balances between periods
"""

from decimal import Decimal
from typing import Dict, List, Optional, TypedDict

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models import (
    ContributionLedger,
    ExpenseLedger,
    ServiceCharge,
    User,
)


class BalanceSheetEntry(TypedDict):
    """Balance sheet entry for an owner in a period."""
    owner_id: int
    username: str
    total_contributions: Decimal
    total_expenses: Decimal
    total_charges: Decimal
    balance: Decimal  # contributions - (expenses + charges)


class BalanceService:
    """Balance calculation and reporting service."""

    def __init__(self, db: Optional[Session] = None):
        """Initialize balance service.
        
        Args:
            db: Database session (optional)
        """
        self.db = db

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

    def get_owner_contributions(self, period_id: int, owner_id: int) -> Decimal:
        """Get total contributions by owner in period.

        Args:
            period_id: Service period ID
            owner_id: Owner ID

        Returns:
            Total contribution amount
        """
        if not self.db:
            return Decimal(0)

        result = (
            self.db.query(func.sum(ContributionLedger.amount))
            .filter(
                ContributionLedger.service_period_id == period_id,
                ContributionLedger.user_id == owner_id
            )
            .scalar()
        )
        return result or Decimal(0)

    def get_period_contributions(self, period_id: int) -> Dict[int, Decimal]:
        """Get all contributions by owner in period.

        Args:
            period_id: Service period ID

        Returns:
            Dict mapping owner_id to total contributions
        """
        if not self.db:
            return {}

        results = (
            self.db.query(
                ContributionLedger.user_id,
                func.sum(ContributionLedger.amount).label("total")
            )
            .filter_by(service_period_id=period_id)
            .group_by(ContributionLedger.user_id)
            .all()
        )
        return {owner_id: total for owner_id, total in results}

    def get_owner_expenses(self, period_id: int, owner_id: int) -> Decimal:
        """Get total allocated expenses for owner in period.

        In the current system, expenses are recorded by payer.
        This returns the amount paid by the owner that they should be reimbursed for.

        Args:
            period_id: Service period ID
            owner_id: Owner ID

        Returns:
            Total expense amount paid by owner
        """
        if not self.db:
            return Decimal(0)

        result = (
            self.db.query(func.sum(ExpenseLedger.amount))
            .filter(
                ExpenseLedger.service_period_id == period_id,
                ExpenseLedger.paid_by_user_id == owner_id
            )
            .scalar()
        )
        return result or Decimal(0)

    def get_period_expenses(self, period_id: int) -> Dict[int, Decimal]:
        """Get all expenses by payer in period.

        Args:
            period_id: Service period ID

        Returns:
            Dict mapping owner_id to total expenses paid
        """
        if not self.db:
            return {}

        results = (
            self.db.query(
                ExpenseLedger.paid_by_user_id,
                func.sum(ExpenseLedger.amount).label("total")
            )
            .filter_by(service_period_id=period_id)
            .group_by(ExpenseLedger.paid_by_user_id)
            .all()
        )
        return {owner_id: total for owner_id, total in results}

    def get_owner_service_charges(self, period_id: int, owner_id: int) -> Decimal:
        """Get total service charges for owner in period.

        Args:
            period_id: Service period ID
            owner_id: Owner ID

        Returns:
            Total service charge amount
        """
        if not self.db:
            return Decimal(0)

        result = (
            self.db.query(func.sum(ServiceCharge.amount))
            .filter_by(service_period_id=period_id, user_id=owner_id)
            .scalar()
        )
        return result or Decimal(0)

    def get_period_service_charges(self, period_id: int) -> Dict[int, Decimal]:
        """Get all service charges by owner in period.

        Args:
            period_id: Service period ID

        Returns:
            Dict mapping owner_id to total service charges
        """
        if not self.db:
            return {}

        results = (
            self.db.query(
                ServiceCharge.user_id,
                func.sum(ServiceCharge.amount).label("total")
            )
            .filter_by(service_period_id=period_id)
            .group_by(ServiceCharge.user_id)
            .all()
        )
        return {owner_id: total for owner_id, total in results}

    def generate_period_balance_sheet(self, period_id: int) -> List[BalanceSheetEntry]:
        """Generate balance sheet for entire period.

        Returns entries for all owners with contributions, expenses, charges, and balance.

        Args:
            period_id: Service period ID

        Returns:
            List of balance sheet entries
        """
        if not self.db:
            return []

        # Get all users and all transaction data
        users = self.db.query(User).all()
        contributions = self.get_period_contributions(period_id)
        expenses = self.get_period_expenses(period_id)
        charges = self.get_period_service_charges(period_id)

        sheet = []
        for user in users:
            contrib = contributions.get(user.id, Decimal(0))
            expense = expenses.get(user.id, Decimal(0))
            charge = charges.get(user.id, Decimal(0))
            balance = contrib - (expense + charge)

            sheet.append(BalanceSheetEntry(
                owner_id=user.id,
                username=user.username,
                total_contributions=contrib,
                total_expenses=expense,
                total_charges=charge,
                balance=balance
            ))

        return sheet

    def get_owner_balance(self, period_id: int, owner_id: int) -> Decimal:
        """Get balance for individual owner in period.

        Balance = Contributions - (Allocated Expenses + Service Charges)

        Args:
            period_id: Service period ID
            owner_id: Owner ID

        Returns:
            Owner's balance (positive = credit, negative = owed)
        """
        if not self.db:
            return Decimal(0)

        contrib = self.get_owner_contributions(period_id, owner_id)
        expense = self.get_owner_expenses(period_id, owner_id)
        charge = self.get_owner_service_charges(period_id, owner_id)

        return contrib - (expense + charge)

    def get_period_total_balance(self, period_id: int) -> Decimal:
        """Get total balance for period (sum of all owner balances).

        Should equal 0 in balanced system (what comes in must go out).

        Args:
            period_id: Service period ID

        Returns:
            Total period balance
        """
        if not self.db:
            return Decimal(0)

        sheet = self.generate_period_balance_sheet(period_id)
        return sum(entry["balance"] for entry in sheet)

    def calculate_all_balances(
        self,
        period_id: int,
    ) -> Dict[int, Decimal]:
        """Calculate all owner balances for a period.

        Balance = Total Contributions - Total Charges

        Args:
            period_id: Service period ID

        Returns:
            Dict mapping owner_id to balance amount
        """
        if not self.db:
            return {}

        sheet = self.generate_period_balance_sheet(period_id)
        return {entry["owner_id"]: entry["balance"] for entry in sheet}


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
        if not self.db:
            return {}

        # Calculate balances from previous period
        sheet = self.generate_period_balance_sheet(from_period_id)
        carried = {}

        for entry in sheet:
            if entry["balance"] != Decimal(0):
                carried[entry["owner_id"]] = entry["balance"]

        return carried

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
        if not self.db:
            return

        # For opening contributions (positive balance)
        for owner_id, balance in opening_balances.items():
            if balance > Decimal(0):
                contrib = ContributionLedger(
                    service_period_id=period_id,
                    owner_id=owner_id,
                    amount=balance,
                    description=f"Opening balance from previous period"
                )
                self.db.add(contrib)

            # For opening charges (negative balance - convert to positive for charge)
            elif balance < Decimal(0):
                charge = ServiceCharge(
                    service_period_id=period_id,
                    user_id=owner_id,
                    description=f"Opening debt from previous period",
                    amount=-balance  # Convert negative to positive
                )
                self.db.add(charge)

        self.db.commit()
