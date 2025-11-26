"""Balance calculation service for computing user and account balances.

Unified Balance Formula: Incoming(To) - Outgoing(From) + Bills
- For OWNER accounts: Display inverted (from organization's perspective, credits are positive)
- For ORGANIZATION accounts: Standard display
- For STAFF accounts: Standard display

This service encapsulates the business logic for balance calculations,
making it testable and reusable across endpoints.
"""

import logging
from typing import Dict, NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.account import Account
from src.models.bill import Bill
from src.models.transaction import Transaction

logger = logging.getLogger(__name__)


class BalanceResult(NamedTuple):
    """Balance calculation result with display information."""

    balance: float
    invert_for_display: bool  # True for OWNER accounts (display negated value)


class BalanceCalculationService:
    """Calculate balances for users and accounts."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def calculate_user_balance(self, user_id: int) -> float:
        """Calculate balance for a user via their account.

        Delegates to calculate_account_balance using the user's account.

        Args:
            user_id: User ID to calculate balance for

        Returns:
            Balance as float (positive = credit, negative = debt)
        """
        # Get user's account
        stmt = select(Account).filter(Account.user_id == user_id)
        result = await self.session.execute(stmt)
        account = result.scalar_one_or_none()

        if not account:
            return 0.0

        return await self.calculate_account_balance(account.id)

    async def calculate_multiple_user_balances(self, user_ids: list[int]) -> Dict[int, float]:
        """Calculate balances for multiple users efficiently.

        Args:
            user_ids: List of user IDs

        Returns:
            Dict mapping user_id to balance (float)
        """
        balances = {}
        for user_id in user_ids:
            balances[user_id] = await self.calculate_user_balance(user_id)
        return balances

    async def calculate_account_balance(self, account_id: int) -> float:
        """Calculate balance for an account.

        Unified formula for all account types:
            Balance = Incoming(To) - Outgoing(From) + Bills

        For OWNER accounts, the balance should be displayed inverted
        (use calculate_account_balance_with_display for UI).

        Args:
            account_id: Account ID to calculate balance for

        Returns:
            Balance as float (raw value, not inverted)
        """
        result = await self.calculate_account_balance_with_display(account_id)
        return result.balance

    async def calculate_account_balance_with_display(
        self, account_id: int
    ) -> BalanceResult:
        """Calculate balance for an account with display information.

        Unified formula for all account types:
            Balance = Incoming(To) - Outgoing(From) + Bills

        Returns BalanceResult with invert_for_display=True for OWNER accounts.

        Args:
            account_id: Account ID to calculate balance for

        Returns:
            BalanceResult with balance and invert_for_display flag
        """
        # Get account to determine type
        account_stmt = select(Account).filter(Account.id == account_id)
        result = await self.session.execute(account_stmt)
        account = result.scalar_one_or_none()

        if not account:
            return BalanceResult(balance=0.0, invert_for_display=False)

        # Get incoming transactions (to_account_id = account_id)
        incoming_stmt = select(Transaction).filter(Transaction.to_account_id == account_id)
        result = await self.session.execute(incoming_stmt)
        incoming = result.scalars().all()
        incoming_total = sum(t.amount for t in incoming if t.amount) or 0

        # Get outgoing transactions (from_account_id = account_id)
        outgoing_stmt = select(Transaction).filter(Transaction.from_account_id == account_id)
        result = await self.session.execute(outgoing_stmt)
        outgoing = result.scalars().all()
        outgoing_total = sum(t.amount for t in outgoing if t.amount) or 0

        # Get bills for this account
        bills_stmt = select(Bill).filter(Bill.account_id == account_id)
        result = await self.session.execute(bills_stmt)
        bills = result.scalars().all()
        bills_total = sum(b.bill_amount for b in bills if b.bill_amount) or 0

        # Unified formula: Incoming - Outgoing + Bills
        balance = float(incoming_total - outgoing_total + bills_total)

        # Determine account type (handle both enum and string)
        account_type = (
            account.account_type.value
            if hasattr(account.account_type, "value")
            else str(account.account_type)
        )

        # OWNER accounts display inverted (from org perspective, their credits are positive)
        invert_for_display = account_type == "owner"

        return BalanceResult(balance=balance, invert_for_display=invert_for_display)
