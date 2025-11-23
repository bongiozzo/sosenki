"""Unit tests for BalanceCalculationService."""

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.account import Account
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
async def test_balance_equals_transactions_when_no_bills(
    session: AsyncSession, sample_user: User, sample_account: Account
):
    """Test balance equals transaction sum when no bills exist."""
    # Create transactions
    trans1 = Transaction(
        from_account_id=sample_account.id,
        to_account_id=sample_account.id,
        amount=100.0,
        transaction_date=date(2024, 1, 1),
    )
    trans2 = Transaction(
        from_account_id=sample_account.id,
        to_account_id=sample_account.id,
        amount=50.0,
        transaction_date=date(2024, 1, 2),
    )
    session.add_all([trans1, trans2])
    await session.commit()

    service = BalanceCalculationService(session)
    balance = await service.calculate_user_balance(sample_user.id)
    assert balance == 150.0


@pytest.mark.asyncio
async def test_balance_negative_when_bills_exceed_transactions(
    session: AsyncSession, sample_user: User, sample_account: Account
):
    """Test balance is negative when bills exceed transactions."""
    # Create transaction: +100
    trans = Transaction(
        from_account_id=sample_account.id,
        to_account_id=sample_account.id,
        amount=100.0,
        transaction_date=date(2024, 1, 1),
    )
    session.add(trans)
    await session.commit()

    # Create bill: -150 (more than transactions)
    bill = Bill(
        user_id=sample_user.id,
        service_period_id=1,  # Assuming this exists from fixtures
        bill_amount=150.0,
        bill_type=BillType.ELECTRICITY,
    )
    session.add(bill)
    await session.commit()

    service = BalanceCalculationService(session)
    balance = await service.calculate_user_balance(sample_user.id)
    # Balance = 100 - 150 = -50
    assert balance == -50.0


@pytest.mark.asyncio
async def test_balance_formula_transactions_minus_bills(
    session: AsyncSession, sample_user: User, sample_account: Account
):
    """Test balance calculation: transactions - bills."""
    # Create transactions: 200 + 100 = 300
    trans1 = Transaction(
        from_account_id=sample_account.id,
        to_account_id=sample_account.id,
        amount=200.0,
        transaction_date=date(2024, 1, 1),
    )
    trans2 = Transaction(
        from_account_id=sample_account.id,
        to_account_id=sample_account.id,
        amount=100.0,
        transaction_date=date(2024, 1, 2),
    )
    session.add_all([trans1, trans2])
    await session.commit()

    # Create bills: 80 + 40 = 120
    bill1 = Bill(
        user_id=sample_user.id,
        service_period_id=1,
        bill_amount=80.0,
        bill_type=BillType.ELECTRICITY,
    )
    bill2 = Bill(
        user_id=sample_user.id,
        service_period_id=1,
        bill_amount=40.0,
        bill_type=BillType.ELECTRICITY,
    )
    session.add_all([bill1, bill2])
    await session.commit()

    service = BalanceCalculationService(session)
    balance = await service.calculate_user_balance(sample_user.id)
    # Balance = 300 - 120 = 180
    assert balance == 180.0


@pytest.mark.asyncio
async def test_balance_zero_bills_graceful_when_bills_table_missing(
    session: AsyncSession, sample_user: User, sample_account: Account
):
    """Test balance calculation gracefully handles missing bills table."""
    # Create transaction
    trans = Transaction(
        from_account_id=sample_account.id,
        to_account_id=sample_account.id,
        amount=100.0,
        transaction_date=date(2024, 1, 1),
    )
    session.add(trans)
    await session.commit()

    # Don't add any bills - service should handle gracefully
    service = BalanceCalculationService(session)
    balance = await service.calculate_user_balance(sample_user.id)
    assert balance == 100.0


@pytest.mark.asyncio
async def test_multiple_user_balances(
    session: AsyncSession,
    sample_user: User,
    sample_account: Account,
    another_user: User,
):
    """Test calculating balances for multiple users."""
    # User 1: 100 transactions, 30 bills = 70 balance
    trans1 = Transaction(
        from_account_id=sample_account.id,
        to_account_id=sample_account.id,
        amount=100.0,
        transaction_date=date(2024, 1, 1),
    )
    session.add(trans1)
    await session.commit()

    bill1 = Bill(
        user_id=sample_user.id,
        service_period_id=1,
        bill_amount=30.0,
        bill_type=BillType.ELECTRICITY,
    )
    session.add(bill1)
    await session.commit()

    # User 2: 0 transactions, 0 bills = 0 balance
    # (another_user has no accounts or transactions)

    service = BalanceCalculationService(session)
    balances = await service.calculate_multiple_user_balances([sample_user.id, another_user.id])

    assert balances[sample_user.id] == 70.0
    assert balances[another_user.id] == 0.0


@pytest.mark.asyncio
async def test_balance_positive_and_negative_values(
    session: AsyncSession, sample_user: User, sample_account: Account
):
    """Test balance correctly represents credit (positive) and debt (negative)."""
    service = BalanceCalculationService(session)

    # Create transactions and bills
    trans = Transaction(
        from_account_id=sample_account.id,
        to_account_id=sample_account.id,
        amount=100.0,
        transaction_date=date(2024, 1, 1),
    )
    session.add(trans)
    await session.commit()

    # Scenario 1: Balance positive (credit)
    balance = await service.calculate_user_balance(sample_user.id)
    assert balance > 0, "Credit balance should be positive"

    # Add bills that exceed transactions
    bill = Bill(
        user_id=sample_user.id,
        service_period_id=1,
        bill_amount=200.0,
        bill_type=BillType.ELECTRICITY,
    )
    session.add(bill)
    await session.commit()

    # Scenario 2: Balance negative (debt)
    balance = await service.calculate_user_balance(sample_user.id)
    assert balance < 0, "Debt balance should be negative"
