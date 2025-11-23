"""Balance calculation service for computing user and owner balances.

Balance Formula: Total Transactions - Total Bills

This service encapsulates the business logic for balance calculations,
making it testable and reusable across endpoints.
"""

import logging
from typing import Dict

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.account import Account
from src.models.bill import Bill
from src.models.property import Property
from src.models.transaction import Transaction

logger = logging.getLogger(__name__)


class BalanceCalculationService:
    """Calculate balances for users based on transactions and bills."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def calculate_user_balance(self, user_id: int) -> float:
        """Calculate balance for a user (transactions - bills).

        Args:
            user_id: User ID to calculate balance for

        Returns:
            Balance as float (positive = credit, negative = debt)
        """
        transactions_total = await self._sum_user_transactions(user_id)
        bills_total = await self._sum_user_electricity_bills(user_id)
        return float(transactions_total - bills_total)

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

    async def _sum_user_transactions(self, user_id: int) -> float:
        """Sum all transactions for a user.

        Transactions involve the user's accounts (either from or to).

        Args:
            user_id: User ID

        Returns:
            Sum of transaction amounts (float)
        """
        # Get user's accounts
        stmt = select(Account).filter(Account.user_id == user_id)
        result = await self.session.execute(stmt)
        user_accounts = result.scalars().all()
        account_ids = [acc.id for acc in user_accounts]

        if not account_ids:
            return 0.0

        # Get transactions involving user's accounts (either from or to)
        stmt = select(Transaction).filter(
            or_(
                Transaction.from_account_id.in_(account_ids),
                Transaction.to_account_id.in_(account_ids),
            )
        )
        result = await self.session.execute(stmt)
        transactions = result.scalars().all()

        total = sum(t.amount for t in transactions if t.amount)
        return float(total) if total else 0.0

    async def _sum_user_electricity_bills(self, user_id: int) -> float:
        """Sum all bills for a user.

        Includes:
        - Bills directly assigned to user (Bill.user_id == user_id)
        - Bills for properties owned by user (property_id in user's properties)

        Args:
            user_id: User ID

        Returns:
            Sum of bill amounts (float), or 0.0 if no bills found
        """
        try:
            # Get user's property IDs
            properties_stmt = select(Property.id).where(Property.owner_id == user_id)
            result = await self.session.execute(properties_stmt)
            property_ids = [row[0] for row in result.all()]

            # Query bills: either directly for user OR for user's properties
            bills_stmt = select(Bill).where(
                or_(
                    Bill.user_id == user_id,
                    Bill.property_id.in_(property_ids) if property_ids else False,
                )
            )
            result = await self.session.execute(bills_stmt)
            bills = result.scalars().all()
            total = sum(b.bill_amount for b in bills if b.bill_amount)
            return float(total) if total else 0.0
        except Exception as e:
            logger.warning(f"Could not fetch bills for user {user_id}: {e}")
            return 0.0
