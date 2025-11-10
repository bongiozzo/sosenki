"""Integration tests for balance sheet generation and balance calculations."""

import pytest
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, User
from src.services.payment_service import PaymentService
from src.services.balance_service import BalanceService


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def users(db_session):
    """Create test users."""
    users_data = [(1, 12345, "alice", "Alice User"), (2, 12346, "bob", "Bob User"), (3, 12347, "charlie", "Charlie User")]
    users = []
    for uid, tgid, username, name in users_data:
        user = User(id=uid, telegram_id=tgid, username=username, name=name)
        db_session.add(user)
        users.append(user)
    db_session.commit()
    return users


class TestBalanceCalculation:
    """Test balance calculation methods."""

    def test_get_owner_contributions(self, db_session, users):
        """Test retrieving owner's total contributions."""
        payment_service = PaymentService(db=db_session)
        balance_service = BalanceService(db=db_session)
        
        period = payment_service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record contributions
        payment_service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("1000.00"),
            date_val=datetime.now()
        )
        payment_service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("500.00"),
            date_val=datetime.now()
        )
        
        total = balance_service.get_owner_contributions(period.id, users[0].id)
        assert total == Decimal("1500.00")

    def test_get_period_contributions(self, db_session, users):
        """Test retrieving all contributions in period."""
        payment_service = PaymentService(db=db_session)
        balance_service = BalanceService(db=db_session)
        
        period = payment_service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record contributions for multiple owners
        payment_service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("1000.00"),
            date_val=datetime.now()
        )
        payment_service.record_contribution(
            period_id=period.id,
            user_id=users[1].id,
            amount=Decimal("2000.00"),
            date_val=datetime.now()
        )
        payment_service.record_contribution(
            period_id=period.id,
            user_id=users[2].id,
            amount=Decimal("1500.00"),
            date_val=datetime.now()
        )
        
        contributions = balance_service.get_period_contributions(period.id)
        
        assert len(contributions) == 3
        assert contributions[users[0].id] == Decimal("1000.00")
        assert contributions[users[1].id] == Decimal("2000.00")
        assert contributions[users[2].id] == Decimal("1500.00")

    def test_get_owner_expenses(self, db_session, users):
        """Test retrieving owner's total allocated expenses."""
        balance_service = BalanceService(db=db_session)
        
        # Direct test without complex expense setup
        # In production, expenses would be calculated from ExpenseLedger
        expenses = balance_service.get_owner_expenses(1, users[0].id)
        
        # Should be 0 for non-existent period
        assert expenses == Decimal("0")

    def test_get_owner_service_charges(self, db_session, users):
        """Test retrieving owner's total service charges."""
        payment_service = PaymentService(db=db_session)
        balance_service = BalanceService(db=db_session)
        
        period = payment_service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record service charges
        payment_service.record_service_charge(
            period_id=period.id,
            user_id=users[0].id,
            description="Maintenance",
            amount=Decimal("200.00")
        )
        payment_service.record_service_charge(
            period_id=period.id,
            user_id=users[0].id,
            description="Repair",
            amount=Decimal("300.00")
        )
        
        charges = balance_service.get_owner_service_charges(period.id, users[0].id)
        assert charges == Decimal("500.00")

    def test_get_owner_balance(self, db_session, users):
        """Test calculating individual owner balance."""
        payment_service = PaymentService(db=db_session)
        balance_service = BalanceService(db=db_session)
        
        period = payment_service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Alice contributes 1000
        payment_service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("1000.00"),
            date_val=datetime.now()
        )
        
        # Alice gets charged 300 (service charge + allocated expense)
        payment_service.record_service_charge(
            period_id=period.id,
            user_id=users[0].id,
            description="Charge",
            amount=Decimal("300.00")
        )
        
        balance = balance_service.get_owner_balance(period.id, users[0].id)
        assert balance == Decimal("700.00")  # 1000 - 300

    def test_get_owner_balance_negative(self, db_session, users):
        """Test balance calculation when owner owes money."""
        payment_service = PaymentService(db=db_session)
        balance_service = BalanceService(db=db_session)
        
        period = payment_service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Alice contributes 500
        payment_service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("500.00"),
            date_val=datetime.now()
        )
        
        # Alice gets charged 800
        payment_service.record_service_charge(
            period_id=period.id,
            user_id=users[0].id,
            description="Large charge",
            amount=Decimal("800.00")
        )
        
        balance = balance_service.get_owner_balance(period.id, users[0].id)
        assert balance == Decimal("-300.00")  # 500 - 800 = -300 (owes 300)


class TestBalanceSheetGeneration:
    """Test balance sheet generation."""

    def test_generate_period_balance_sheet(self, db_session, users):
        """Test generating complete balance sheet for period."""
        payment_service = PaymentService(db=db_session)
        balance_service = BalanceService(db=db_session)
        
        period = payment_service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Set up different financial positions for each owner
        # Alice: contributes 1000, charged 200 → balance 800
        payment_service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("1000.00"),
            date_val=datetime.now()
        )
        payment_service.record_service_charge(
            period_id=period.id,
            user_id=users[0].id,
            description="Charge",
            amount=Decimal("200.00")
        )
        
        # Bob: contributes 1500, charged 300 → balance 1200
        payment_service.record_contribution(
            period_id=period.id,
            user_id=users[1].id,
            amount=Decimal("1500.00"),
            date_val=datetime.now()
        )
        payment_service.record_service_charge(
            period_id=period.id,
            user_id=users[1].id,
            description="Charge",
            amount=Decimal("300.00")
        )
        
        # Charlie: contributes 800, charged 500 → balance 300
        payment_service.record_contribution(
            period_id=period.id,
            user_id=users[2].id,
            amount=Decimal("800.00"),
            date_val=datetime.now()
        )
        payment_service.record_service_charge(
            period_id=period.id,
            user_id=users[2].id,
            description="Charge",
            amount=Decimal("500.00")
        )
        
        sheet = balance_service.generate_period_balance_sheet(period.id)
        
        assert len(sheet) == 3
        
        # Verify entries
        alice_entry = next((e for e in sheet if e["owner_id"] == users[0].id), None)
        assert alice_entry is not None
        assert alice_entry["balance"] == Decimal("800.00")
        assert alice_entry["total_contributions"] == Decimal("1000.00")
        assert alice_entry["total_charges"] == Decimal("200.00")

    def test_balance_sheet_includes_all_users(self, db_session, users):
        """Test balance sheet includes all users even if no transactions."""
        payment_service = PaymentService(db=db_session)
        balance_service = BalanceService(db=db_session)
        
        period = payment_service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Only Alice has transactions
        payment_service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("1000.00"),
            date_val=datetime.now()
        )
        
        sheet = balance_service.generate_period_balance_sheet(period.id)
        
        # All three users should be in sheet
        assert len(sheet) == 3
        
        # Bob and Charlie have zero balances
        bob_entry = next((e for e in sheet if e["owner_id"] == users[1].id), None)
        charlie_entry = next((e for e in sheet if e["owner_id"] == users[2].id), None)
        
        assert bob_entry is not None
        assert bob_entry["balance"] == Decimal("0")
        assert charlie_entry is not None
        assert charlie_entry["balance"] == Decimal("0")

    def test_get_period_total_balance(self, db_session, users):
        """Test total period balance calculation."""
        payment_service = PaymentService(db=db_session)
        balance_service = BalanceService(db=db_session)
        
        period = payment_service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Total in: 3300
        payment_service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("1000.00"),
            date_val=datetime.now()
        )
        payment_service.record_contribution(
            period_id=period.id,
            user_id=users[1].id,
            amount=Decimal("1200.00"),
            date_val=datetime.now()
        )
        payment_service.record_contribution(
            period_id=period.id,
            user_id=users[2].id,
            amount=Decimal("1100.00"),
            date_val=datetime.now()
        )
        
        # Total charges: 3300
        payment_service.record_service_charge(
            period_id=period.id,
            user_id=users[0].id,
            description="Charge",
            amount=Decimal("1100.00")
        )
        payment_service.record_service_charge(
            period_id=period.id,
            user_id=users[1].id,
            description="Charge",
            amount=Decimal("1100.00")
        )
        payment_service.record_service_charge(
            period_id=period.id,
            user_id=users[2].id,
            description="Charge",
            amount=Decimal("1100.00")
        )
        
        total = balance_service.get_period_total_balance(period.id)
        
        # In balanced system, total should be 0 (all money in = all money out)
        assert total == Decimal("0")

    def test_calculate_all_balances(self, db_session, users):
        """Test getting all owner balances at once."""
        payment_service = PaymentService(db=db_session)
        balance_service = BalanceService(db=db_session)
        
        period = payment_service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Set up balances
        payment_service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("1000.00"),
            date_val=datetime.now()
        )
        payment_service.record_service_charge(
            period_id=period.id,
            user_id=users[0].id,
            description="Charge",
            amount=Decimal("200.00")
        )
        
        balances = balance_service.calculate_all_balances(period.id)
        
        assert users[0].id in balances
        assert balances[users[0].id] == Decimal("800.00")
        # Other users have 0 balance
        assert balances.get(users[1].id, Decimal("0")) == Decimal("0")
        assert balances.get(users[2].id, Decimal("0")) == Decimal("0")


class TestBalanceSheetEdgeCases:
    """Test edge cases in balance calculations."""

    def test_empty_period_balance_sheet(self, db_session, users):
        """Test balance sheet for period with no transactions."""
        balance_service = BalanceService(db=db_session)
        payment_service = PaymentService(db=db_session)
        
        period = payment_service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        sheet = balance_service.generate_period_balance_sheet(period.id)
        
        # Should still include all users with zero balances
        assert len(sheet) == 3
        assert all(entry["balance"] == Decimal("0") for entry in sheet)

    def test_fractional_allocations(self, db_session, users):
        """Test balance calculation with fractional amounts."""
        payment_service = PaymentService(db=db_session)
        balance_service = BalanceService(db=db_session)
        
        period = payment_service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Fractional contribution
        payment_service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("333.33"),
            date_val=datetime.now()
        )
        
        # Fractional charge
        payment_service.record_service_charge(
            period_id=period.id,
            user_id=users[0].id,
            description="Charge",
            amount=Decimal("111.11")
        )
        
        balance = balance_service.get_owner_balance(period.id, users[0].id)
        assert balance == Decimal("222.22")
