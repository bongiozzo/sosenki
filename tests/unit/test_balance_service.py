"""Unit tests for BalanceCalculationService.

Balance Formula (Unified):
- All accounts: Balance = Incoming(To) - Outgoing(From) + Bills

For user accounts with outgoing payments and bills:
- Incoming = 0 (users don't receive payments TO their account)
- Outgoing = payments made (FROM account)
- Bills = bills owed

So: Balance = 0 - Payments + Bills = Bills - Payments
- Positive = user owes money (bills > payments)
- Negative = user has credit (payments > bills, overpaid)

Note: OWNER accounts display inverted values (use calculate_account_balance_with_display)
"""

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.account import Account, AccountType
from src.models.bill import Bill, BillType
from src.models.transaction import Transaction
from src.models.user import User
from src.services.balance_service import BalanceCalculationService


@pytest.mark.asyncio
async def test_balance_zero_when_no_transactions_and_no_bills(
    session: AsyncSession, sample_user: User
):
    """Test balance is 0 when user has no transactions or bills."""
    service = BalanceCalculationService(session)
    balance = await service.calculate_user_balance(sample_user.id)
    assert balance == 0.0


@pytest.mark.asyncio
async def test_user_balance_negative_when_payments_exceed_bills(
    session: AsyncSession, sample_user: User, sample_account: Account
):
    """Test user balance is negative (credit) when payments exceed bills.

    For accounts: Balance = Incoming - Outgoing + Bills
    When Outgoing (payments) > Bills: Balance is negative (user has credit)
    """
    # Create a destination account (community fund where user pays TO)
    community_fund = Account(
        name="Community Fund",
        account_type=AccountType.ORGANIZATION,
    )
    session.add(community_fund)
    await session.commit()

    # Create outgoing transactions (user pays to community) = 200
    trans1 = Transaction(
        from_account_id=sample_account.id,  # FROM user
        to_account_id=community_fund.id,  # TO community
        amount=100.0,
        transaction_date=date(2024, 1, 1),
    )
    trans2 = Transaction(
        from_account_id=sample_account.id,
        to_account_id=community_fund.id,
        amount=100.0,
        transaction_date=date(2024, 1, 2),
    )
    session.add_all([trans1, trans2])
    await session.commit()

    # Create bills = 150 (less than payments)
    bill = Bill(
        account_id=sample_account.id,
        service_period_id=1,
        bill_amount=150.0,
        bill_type=BillType.ELECTRICITY,
    )
    session.add(bill)
    await session.commit()

    service = BalanceCalculationService(session)
    balance = await service.calculate_user_balance(sample_user.id)
    # Balance = 0 (incoming) - 200 (outgoing) + 150 (bills) = -50 (credit)
    assert balance == -50.0


@pytest.mark.asyncio
async def test_user_balance_positive_when_bills_exceed_payments(
    session: AsyncSession, sample_user: User, sample_account: Account
):
    """Test user balance is positive (debt) when bills exceed payments.

    For accounts: Balance = Incoming - Outgoing + Bills
    When Bills > Outgoing (payments): Balance is positive (user owes money)
    """
    # Create a destination account
    community_fund = Account(
        name="Community Fund",
        account_type=AccountType.ORGANIZATION,
    )
    session.add(community_fund)
    await session.commit()

    # Create outgoing transaction (user pays) = 100
    trans = Transaction(
        from_account_id=sample_account.id,
        to_account_id=community_fund.id,
        amount=100.0,
        transaction_date=date(2024, 1, 1),
    )
    session.add(trans)
    await session.commit()

    # Create bill = 150 (more than payments)
    bill = Bill(
        account_id=sample_account.id,
        service_period_id=1,
        bill_amount=150.0,
        bill_type=BillType.ELECTRICITY,
    )
    session.add(bill)
    await session.commit()

    service = BalanceCalculationService(session)
    balance = await service.calculate_user_balance(sample_user.id)
    # Balance = 0 (incoming) - 100 (outgoing) + 150 (bills) = +50 (debt)
    assert balance == 50.0


@pytest.mark.asyncio
async def test_user_balance_formula_bills_minus_payments(
    session: AsyncSession, sample_user: User, sample_account: Account
):
    """Test user balance formula: Incoming - Outgoing + Bills."""
    # Create a destination account
    community_fund = Account(
        name="Community Fund",
        account_type=AccountType.ORGANIZATION,
    )
    session.add(community_fund)
    await session.commit()

    # Create outgoing transactions (payments): 200 + 100 = 300
    trans1 = Transaction(
        from_account_id=sample_account.id,
        to_account_id=community_fund.id,
        amount=200.0,
        transaction_date=date(2024, 1, 1),
    )
    trans2 = Transaction(
        from_account_id=sample_account.id,
        to_account_id=community_fund.id,
        amount=100.0,
        transaction_date=date(2024, 1, 2),
    )
    session.add_all([trans1, trans2])
    await session.commit()

    # Create bills: 80 + 40 = 120
    bill1 = Bill(
        account_id=sample_account.id,
        service_period_id=1,
        bill_amount=80.0,
        bill_type=BillType.ELECTRICITY,
    )
    bill2 = Bill(
        account_id=sample_account.id,
        service_period_id=1,
        bill_amount=40.0,
        bill_type=BillType.ELECTRICITY,
    )
    session.add_all([bill1, bill2])
    await session.commit()

    service = BalanceCalculationService(session)
    balance = await service.calculate_user_balance(sample_user.id)
    # Balance = 0 (incoming) - 300 (outgoing) + 120 (bills) = -180 (credit)
    assert balance == -180.0


@pytest.mark.asyncio
async def test_user_balance_equals_negative_payments_when_no_bills(
    session: AsyncSession, sample_user: User, sample_account: Account
):
    """Test user balance equals negative payments when no bills exist."""
    # Create a destination account
    community_fund = Account(
        name="Community Fund",
        account_type=AccountType.ORGANIZATION,
    )
    session.add(community_fund)
    await session.commit()

    # Create outgoing transaction (user pays) = 100
    trans = Transaction(
        from_account_id=sample_account.id,
        to_account_id=community_fund.id,
        amount=100.0,
        transaction_date=date(2024, 1, 1),
    )
    session.add(trans)
    await session.commit()

    # No bills - balance should equal negative payments
    service = BalanceCalculationService(session)
    balance = await service.calculate_user_balance(sample_user.id)
    # Balance = 0 (incoming) - 100 (outgoing) + 0 (bills) = -100 (credit)
    assert balance == -100.0


@pytest.mark.asyncio
async def test_multiple_user_balances(
    session: AsyncSession,
    sample_user: User,
    sample_account: Account,
    another_user: User,
):
    """Test calculating balances for multiple users."""
    # Create a destination account
    community_fund = Account(
        name="Community Fund",
        account_type=AccountType.ORGANIZATION,
    )
    session.add(community_fund)
    await session.commit()

    # User 1: 100 payments, 30 bills = -70 balance (credit: payments > bills)
    trans1 = Transaction(
        from_account_id=sample_account.id,
        to_account_id=community_fund.id,
        amount=100.0,
        transaction_date=date(2024, 1, 1),
    )
    session.add(trans1)
    await session.commit()

    bill1 = Bill(
        account_id=sample_account.id,
        service_period_id=1,
        bill_amount=30.0,
        bill_type=BillType.ELECTRICITY,
    )
    session.add(bill1)
    await session.commit()

    # User 2: 0 transactions, 0 bills = 0 balance

    service = BalanceCalculationService(session)
    balances = await service.calculate_multiple_user_balances([sample_user.id, another_user.id])

    # Balance = 0 (incoming) - 100 (outgoing) + 30 (bills) = -70 (credit)
    assert balances[sample_user.id] == -70.0
    assert balances[another_user.id] == 0.0


@pytest.mark.asyncio
async def test_user_balance_credit_and_debt_states(
    session: AsyncSession, sample_user: User, sample_account: Account
):
    """Test balance correctly represents credit (negative) and debt (positive).

    With unified formula: Balance = Incoming - Outgoing + Bills
    - Negative = user has credit (overpaid: payments > bills)
    - Positive = user owes money (debt: bills > payments)
    """
    # Create a destination account
    community_fund = Account(
        name="Community Fund",
        account_type=AccountType.ORGANIZATION,
    )
    session.add(community_fund)
    await session.commit()

    service = BalanceCalculationService(session)

    # Create outgoing transaction (payment)
    trans = Transaction(
        from_account_id=sample_account.id,
        to_account_id=community_fund.id,
        amount=100.0,
        transaction_date=date(2024, 1, 1),
    )
    session.add(trans)
    await session.commit()

    # Scenario 1: Balance negative (credit) - paid 100, no bills
    # Balance = 0 - 100 + 0 = -100
    balance = await service.calculate_user_balance(sample_user.id)
    assert balance < 0, "Credit balance should be negative (overpaid)"

    # Add bills that exceed payments
    bill = Bill(
        account_id=sample_account.id,
        service_period_id=1,
        bill_amount=200.0,
        bill_type=BillType.ELECTRICITY,
    )
    session.add(bill)
    await session.commit()

    # Scenario 2: Balance positive (debt) - paid 100, bills 200
    # Balance = 0 - 100 + 200 = 100
    balance = await service.calculate_user_balance(sample_user.id)
    assert balance > 0, "Debt balance should be positive (owes money)"
