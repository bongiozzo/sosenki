"""Integration tests for service period workflows."""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.models import Base, ServicePeriod, PeriodStatus, ContributionLedger, User
from src.services.payment_service import PaymentService


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
def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(id=1, telegram_id=12345, username="testuser", name="Test User")
    db_session.add(user)
    db_session.commit()
    return user


class TestPeriodLifecycle:
    """Test complete period lifecycle with database."""

    def test_create_and_retrieve_period(self, db_session):
        """Test creating a period and retrieving it."""
        service = PaymentService(db=db_session)
        
        start = date(2025, 11, 1)
        end = date(2025, 11, 30)
        
        # Create period
        period = service.create_period(
            name="November 2025",
            start_date=start,
            end_date=end,
            description="Monthly billing"
        )
        
        assert period.id is not None
        assert period.name == "November 2025"
        
        # Retrieve period
        retrieved = service.get_period(period.id)
        assert retrieved is not None
        assert retrieved.name == "November 2025"
        assert retrieved.status == PeriodStatus.OPEN

    def test_list_multiple_periods(self, db_session):
        """Test listing multiple periods."""
        service = PaymentService(db=db_session)
        
        # Create multiple periods
        periods_data = [
            ("September 2025", date(2025, 9, 1), date(2025, 9, 30)),
            ("October 2025", date(2025, 10, 1), date(2025, 10, 31)),
            ("November 2025", date(2025, 11, 1), date(2025, 11, 30)),
        ]
        
        created_periods = []
        for name, start, end in periods_data:
            period = service.create_period(name, start, end)
            created_periods.append(period)
        
        # List all periods
        all_periods = service.list_periods()
        assert len(all_periods) == 3
        
        # Should be sorted by start_date descending (most recent first)
        assert all_periods[0].name == "November 2025"
        assert all_periods[1].name == "October 2025"
        assert all_periods[2].name == "September 2025"

    def test_close_and_reopen_period(self, db_session):
        """Test closing and reopening a period."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Test Period",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        assert period.status == PeriodStatus.OPEN
        
        # Close period
        closed = service.close_period(period.id)
        assert closed.status == PeriodStatus.CLOSED
        assert closed.closed_at is not None
        
        # Verify it's closed in database
        retrieved = service.get_period(period.id)
        assert retrieved.status == PeriodStatus.CLOSED
        
        # Reopen period
        reopened = service.reopen_period(period.id)
        assert reopened.status == PeriodStatus.OPEN
        assert reopened.closed_at is None

    def test_cannot_close_nonexistent_period(self, db_session):
        """Test closing nonexistent period raises error."""
        service = PaymentService(db=db_session)
        
        with pytest.raises(ValueError, match="Period 999 not found"):
            service.close_period(999)

    def test_cannot_close_already_closed_period(self, db_session):
        """Test closing already-closed period raises error."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Test",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        service.close_period(period.id)
        
        # Try to close again
        with pytest.raises(ValueError, match="already closed"):
            service.close_period(period.id)

    def test_cannot_reopen_already_open_period(self, db_session):
        """Test reopening already-open period raises error."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Test",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Try to reopen already-open period
        with pytest.raises(ValueError, match="already open"):
            service.reopen_period(period.id)


class TestPeriodTransactions:
    """Test transactions within periods."""

    def test_record_and_retrieve_contribution(self, db_session, sample_user):
        """Test recording and retrieving a contribution."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record contribution
        now = datetime.now()
        contribution = service.record_contribution(
            period_id=period.id,
            user_id=sample_user.id,
            amount=Decimal("500.00"),
            date_val=now,
            comment="November payment"
        )
        
        assert contribution.id is not None
        assert contribution.amount == Decimal("500.00")
        
        # Retrieve contributions
        contributions = service.get_contributions(period.id)
        assert len(contributions) == 1
        assert contributions[0].amount == Decimal("500.00")

    def test_get_owner_contributions_sum(self, db_session, sample_user):
        """Test calculating owner's total contributions."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record multiple contributions
        service.record_contribution(period.id, sample_user.id, Decimal("200.00"), datetime.now())
        service.record_contribution(period.id, sample_user.id, Decimal("300.00"), datetime.now())
        
        total = service.get_owner_contributions(period.id, sample_user.id)
        assert total == Decimal("500.00")

    def test_get_owner_contributions_different_users(self, db_session, sample_user):
        """Test contributions only sum for specific user."""
        service = PaymentService(db=db_session)
        
        # Create second user
        user2 = User(id=2, telegram_id=54321, username="testuser2", name="Test User 2")
        db_session.add(user2)
        db_session.commit()
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record contributions from different users
        service.record_contribution(period.id, sample_user.id, Decimal("200.00"), datetime.now())
        service.record_contribution(period.id, user2.id, Decimal("300.00"), datetime.now())
        
        user1_total = service.get_owner_contributions(period.id, sample_user.id)
        user2_total = service.get_owner_contributions(period.id, user2.id)
        
        assert user1_total == Decimal("200.00")
        assert user2_total == Decimal("300.00")

    def test_edit_contribution_in_open_period(self, db_session, sample_user):
        """Test editing contribution in OPEN period."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        contribution = service.record_contribution(
            period.id, sample_user.id, Decimal("500.00"), datetime.now()
        )
        
        # Edit contribution
        edited = service.edit_contribution(contribution.id, amount=Decimal("600.00"))
        assert edited.amount == Decimal("600.00")

    def test_cannot_edit_contribution_in_closed_period(self, db_session, sample_user):
        """Test cannot edit contribution in CLOSED period."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        contribution = service.record_contribution(
            period.id, sample_user.id, Decimal("500.00"), datetime.now()
        )
        
        # Close period
        service.close_period(period.id)
        
        # Try to edit
        with pytest.raises(ValueError, match="Cannot edit contribution in closed period"):
            service.edit_contribution(contribution.id, amount=Decimal("600.00"))

    def test_cannot_record_contribution_in_closed_period(self, db_session, sample_user):
        """Test cannot record contribution in CLOSED period."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Close period
        service.close_period(period.id)
        
        # Try to record contribution
        with pytest.raises(ValueError, match="not open for contributions"):
            service.record_contribution(
                period.id, sample_user.id, Decimal("500.00"), datetime.now()
            )

    def test_record_expense(self, db_session, sample_user):
        """Test recording and retrieving expenses."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record expense
        expense = service.record_expense(
            period.id,
            paid_by_user_id=sample_user.id,
            amount=Decimal("1500.00"),
            payment_type="Water",
            date_val=datetime.now(),
            vendor="City Water",
            description="Q4 water bill"
        )
        
        assert expense.id is not None
        assert expense.amount == Decimal("1500.00")
        assert expense.vendor == "City Water"
        
        # Retrieve expenses
        expenses = service.get_expenses(period.id)
        assert len(expenses) == 1

    def test_get_expenses_paid_by_user(self, db_session, sample_user):
        """Test getting expenses paid by specific user."""
        service = PaymentService(db=db_session)
        
        user2 = User(id=2, telegram_id=54321, username="testuser2", name="Test User 2")
        db_session.add(user2)
        db_session.commit()
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record expenses from different users
        service.record_expense(
            period.id, sample_user.id, Decimal("1000.00"), "Water", datetime.now()
        )
        service.record_expense(
            period.id, user2.id, Decimal("500.00"), "Electric", datetime.now()
        )
        
        # Get expenses paid by user 1
        user1_expenses = service.get_paid_by_user(period.id, sample_user.id)
        assert len(user1_expenses) == 1
        assert user1_expenses[0].amount == Decimal("1000.00")

    def test_record_service_charge(self, db_session, sample_user):
        """Test recording service charges."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        charge = service.record_service_charge(
            period.id,
            user_id=sample_user.id,
            description="Late fee",
            amount=Decimal("50.00")
        )
        
        assert charge.id is not None
        assert charge.amount == Decimal("50.00")
        
        # Retrieve charges
        charges = service.get_service_charges(period.id)
        assert len(charges) == 1

    def test_transaction_history(self, db_session, sample_user):
        """Test getting complete transaction history."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record various transactions
        service.record_contribution(period.id, sample_user.id, Decimal("500.00"), datetime.now())
        service.record_expense(
            period.id, sample_user.id, Decimal("1500.00"), "Water", datetime.now()
        )
        service.record_service_charge(
            period.id, sample_user.id, "Fee", Decimal("25.00")
        )
        
        history = service.get_transaction_history(period.id)
        assert len(history) == 3
