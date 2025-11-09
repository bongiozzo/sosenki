"""Payment service for recording and managing financial transactions.

Provides methods for:
- Recording contributions (owner payments)
- Recording expenses (community charges)
- Managing service periods (OPEN/CLOSED)
- Recording service charges
- Transaction history and editing (in OPEN periods)
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy.orm import Session


class PaymentService:
    """Core financial operations service."""

    def __init__(self, db: Optional[Session] = None):
        """Initialize payment service.

        Args:
            db: SQLAlchemy database session (optional for now)
        """
        self.db = db

    def create_period(
        self,
        name: str,
        start_date,
        end_date,
        description: Optional[str] = None,
    ):
        """Create a new service period.

        Args:
            name: Period identifier (e.g., "Nov 2025")
            start_date: Period start date
            end_date: Period end date
            description: Optional notes

        Returns:
            Created ServicePeriod object
        """
        pass

    def get_period(self, period_id: int):
        """Get service period by ID.

        Args:
            period_id: Period ID

        Returns:
            ServicePeriod object or None
        """
        pass

    def list_periods(self):
        """List all service periods.

        Returns:
            List of ServicePeriod objects
        """
        pass

    def close_period(self, period_id: int):
        """Close a service period (finalize balances).

        Transitions period from OPEN to CLOSED.
        Prevents further transactions.

        Args:
            period_id: Period to close

        Returns:
            Updated ServicePeriod object
        """
        pass

    def reopen_period(self, period_id: int):
        """Reopen a closed period for corrections.

        Transitions period from CLOSED to OPEN.
        Allows transaction editing/adding.

        Args:
            period_id: Period to reopen

        Returns:
            Updated ServicePeriod object
        """
        pass

    def record_contribution(
        self,
        period_id: int,
        user_id: int,
        amount: Decimal,
        date: datetime,
        comment: Optional[str] = None,
    ):
        """Record owner contribution (payment).

        Args:
            period_id: Service period ID
            user_id: Owner ID
            amount: Contribution amount
            date: Date of contribution
            comment: Optional notes

        Returns:
            Created ContributionLedger object
        """
        pass

    def get_contributions(self, period_id: int):
        """List all contributions in period.

        Args:
            period_id: Period ID

        Returns:
            List of ContributionLedger objects
        """
        pass

    def get_owner_contributions(self, period_id: int, owner_id: int):
        """Get cumulative contributions for owner in period.

        Args:
            period_id: Period ID
            owner_id: Owner ID

        Returns:
            Total contribution amount (Decimal)
        """
        pass

    def edit_contribution(
        self,
        contribution_id: int,
        amount: Optional[Decimal] = None,
        comment: Optional[str] = None,
    ):
        """Edit contribution in OPEN period.

        Args:
            contribution_id: Contribution ID
            amount: New amount (optional)
            comment: New comment (optional)

        Returns:
            Updated ContributionLedger object
        """
        pass

    def record_expense(
        self,
        period_id: int,
        paid_by_user_id: int,
        amount: Decimal,
        payment_type: str,
        date: datetime,
        vendor: Optional[str] = None,
        description: Optional[str] = None,
        budget_item_id: Optional[int] = None,
    ):
        """Record community expense.

        Args:
            period_id: Service period ID
            paid_by_user_id: User who paid the expense
            amount: Expense amount
            payment_type: Category of expense
            date: Date of expense
            vendor: Vendor/service provider (optional)
            description: Details (optional)
            budget_item_id: Reference to budget item (optional)

        Returns:
            Created ExpenseLedger object
        """
        pass

    def get_expenses(self, period_id: int):
        """List all expenses in period.

        Args:
            period_id: Period ID

        Returns:
            List of ExpenseLedger objects
        """
        pass

    def get_paid_by_user(self, period_id: int, user_id: int):
        """Get expenses paid by specific user.

        Args:
            period_id: Period ID
            user_id: Payer user ID

        Returns:
            List of ExpenseLedger objects
        """
        pass

    def edit_expense(
        self,
        expense_id: int,
        amount: Optional[Decimal] = None,
        payment_type: Optional[str] = None,
        vendor: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """Edit expense in OPEN period.

        Args:
            expense_id: Expense ID
            amount: New amount (optional)
            payment_type: New type (optional)
            vendor: New vendor (optional)
            description: New description (optional)

        Returns:
            Updated ExpenseLedger object
        """
        pass

    def record_service_charge(
        self,
        period_id: int,
        user_id: int,
        description: str,
        amount: Decimal,
    ):
        """Record service charge for specific owner.

        Args:
            period_id: Period ID
            user_id: Owner to charge
            description: Charge description
            amount: Charge amount

        Returns:
            Created ServiceCharge object
        """
        pass

    def get_service_charges(self, period_id: int):
        """List all service charges in period.

        Args:
            period_id: Period ID

        Returns:
            List of ServiceCharge objects
        """
        pass

    def get_transaction_history(
        self,
        period_id: int,
        user_id: Optional[int] = None,
    ):
        """Get complete transaction history for period.

        Returns contributions, expenses, and charges combined and sorted by date.

        Args:
            period_id: Period ID
            user_id: Optional - filter to specific owner

        Returns:
            List of transactions sorted by date
        """
        pass
