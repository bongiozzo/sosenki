"""Integration tests for expense workflows."""

import pytest
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, User
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
def users(db_session):
    """Create multiple test users."""
    users_data = [
        (1, 12345, "alice", "Alice User"),
        (2, 12346, "bob", "Bob User"),
        (3, 12347, "charlie", "Charlie User"),
    ]
    
    users = []
    for uid, tgid, username, name in users_data:
        user = User(id=uid, telegram_id=tgid, username=username, name=name)
        db_session.add(user)
        users.append(user)
    
    db_session.commit()
    return users


class TestExpenseWorkflows:
    """Test complete expense management workflows."""

    def test_record_single_expense(self, db_session, users):
        """Test recording a single expense."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record expense
        expense = service.record_expense(
            period_id=period.id,
            paid_by_user_id=users[0].id,
            amount=Decimal("1500.00"),
            payment_type="Water",
            date_val=datetime.now(),
            vendor="City Water Works",
            description="Q4 water bill"
        )
        
        assert expense.id is not None
        assert expense.amount == Decimal("1500.00")
        assert expense.paid_by_user_id == users[0].id
        assert expense.payment_type == "Water"
        assert expense.vendor == "City Water Works"
        
        # Verify retrieval
        expenses = service.get_expenses(period.id)
        assert len(expenses) == 1
        assert expenses[0].id == expense.id

    def test_record_multiple_expenses(self, db_session, users):
        """Test recording multiple expenses."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record multiple expenses
        expenses_data = [
            ("Water", Decimal("1500.00"), "City Water"),
            ("Electric", Decimal("2000.00"), "Power Corp"),
            ("Maintenance", Decimal("800.00"), "Fix-It Co"),
        ]
        
        for payment_type, amount, vendor in expenses_data:
            service.record_expense(
                period_id=period.id,
                paid_by_user_id=users[0].id,
                amount=amount,
                payment_type=payment_type,
                date_val=datetime.now(),
                vendor=vendor
            )
        
        # Verify all recorded
        expenses = service.get_expenses(period.id)
        assert len(expenses) == 3

    def test_expenses_paid_by_different_users(self, db_session, users):
        """Test recording expenses paid by different users."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record expenses paid by different users
        service.record_expense(
            period_id=period.id,
            paid_by_user_id=users[0].id,
            amount=Decimal("1000.00"),
            payment_type="Water",
            date_val=datetime.now()
        )
        service.record_expense(
            period_id=period.id,
            paid_by_user_id=users[1].id,
            amount=Decimal("1500.00"),
            payment_type="Electric",
            date_val=datetime.now()
        )
        
        # Get expenses by payer
        user0_expenses = service.get_paid_by_user(period.id, users[0].id)
        user1_expenses = service.get_paid_by_user(period.id, users[1].id)
        
        assert len(user0_expenses) == 1
        assert len(user1_expenses) == 1
        assert user0_expenses[0].amount == Decimal("1000.00")
        assert user1_expenses[0].amount == Decimal("1500.00")

    def test_expense_chronological_ordering(self, db_session, users):
        """Test expenses are ordered chronologically."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record expenses with different dates
        dates = [
            datetime(2025, 11, 15, 10, 0),
            datetime(2025, 11, 10, 14, 30),
            datetime(2025, 11, 20, 9, 15),
        ]
        
        for date_val in dates:
            service.record_expense(
                period_id=period.id,
                paid_by_user_id=users[0].id,
                amount=Decimal("500.00"),
                payment_type="Water",
                date_val=date_val
            )
        
        # Retrieve and verify ordering
        expenses = service.get_expenses(period.id)
        retrieved_dates = [e.date for e in expenses]
        
        # Should be in chronological order
        assert retrieved_dates == sorted(retrieved_dates)

    def test_edit_expense_amount(self, db_session, users):
        """Test editing expense amount."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        expense = service.record_expense(
            period_id=period.id,
            paid_by_user_id=users[0].id,
            amount=Decimal("1000.00"),
            payment_type="Water",
            date_val=datetime.now()
        )
        
        # Edit amount
        edited = service.edit_expense(expense.id, amount=Decimal("1200.00"))
        
        assert edited.amount == Decimal("1200.00")

    def test_edit_expense_payment_type(self, db_session, users):
        """Test editing expense payment type."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        expense = service.record_expense(
            period_id=period.id,
            paid_by_user_id=users[0].id,
            amount=Decimal("1000.00"),
            payment_type="Water",
            date_val=datetime.now()
        )
        
        # Edit payment type
        edited = service.edit_expense(expense.id, payment_type="Water & Sewer")
        
        assert edited.payment_type == "Water & Sewer"

    def test_edit_expense_vendor(self, db_session, users):
        """Test editing expense vendor."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        expense = service.record_expense(
            period_id=period.id,
            paid_by_user_id=users[0].id,
            amount=Decimal("1000.00"),
            payment_type="Water",
            date_val=datetime.now(),
            vendor="Old Vendor"
        )
        
        # Edit vendor
        edited = service.edit_expense(expense.id, vendor="New Vendor")
        
        assert edited.vendor == "New Vendor"

    def test_edit_expense_description(self, db_session, users):
        """Test editing expense description."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        expense = service.record_expense(
            period_id=period.id,
            paid_by_user_id=users[0].id,
            amount=Decimal("1000.00"),
            payment_type="Water",
            date_val=datetime.now(),
            description="Old description"
        )
        
        # Edit description
        edited = service.edit_expense(
            expense.id,
            description="Updated description"
        )
        
        assert edited.description == "Updated description"

    def test_expense_with_budget_item(self, db_session, users):
        """Test recording expense linked to budget item."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record with budget item
        expense = service.record_expense(
            period_id=period.id,
            paid_by_user_id=users[0].id,
            amount=Decimal("1500.00"),
            payment_type="Water",
            date_val=datetime.now(),
            budget_item_id=1
        )
        
        assert expense.budget_item_id == 1

    def test_cannot_record_expense_in_closed_period(self, db_session, users):
        """Test cannot record expense in CLOSED period."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Close period
        service.close_period(period.id)
        
        # Try to record expense
        with pytest.raises(ValueError, match="not open for expenses"):
            service.record_expense(
                period_id=period.id,
                paid_by_user_id=users[0].id,
                amount=Decimal("1000.00"),
                payment_type="Water",
                date_val=datetime.now()
            )

    def test_record_expense_after_reopening_closed_period(self, db_session, users):
        """Test can record expense after reopening closed period."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record initial expense
        service.record_expense(
            period_id=period.id,
            paid_by_user_id=users[0].id,
            amount=Decimal("1000.00"),
            payment_type="Water",
            date_val=datetime.now()
        )
        
        # Close period
        service.close_period(period.id)
        
        # Reopen period
        service.reopen_period(period.id)
        
        # Should be able to record again
        service.record_expense(
            period_id=period.id,
            paid_by_user_id=users[0].id,
            amount=Decimal("500.00"),
            payment_type="Electric",
            date_val=datetime.now()
        )
        
        # Verify both recorded
        expenses = service.get_expenses(period.id)
        assert len(expenses) == 2

    def test_cannot_edit_expense_in_closed_period(self, db_session, users):
        """Test cannot edit expense in CLOSED period."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        expense = service.record_expense(
            period_id=period.id,
            paid_by_user_id=users[0].id,
            amount=Decimal("1000.00"),
            payment_type="Water",
            date_val=datetime.now()
        )
        
        # Close period
        service.close_period(period.id)
        
        # Try to edit
        with pytest.raises(ValueError, match="Cannot edit expense in closed period"):
            service.edit_expense(expense.id, amount=Decimal("1200.00"))

    def test_expense_validation_negative_amount(self, db_session, users):
        """Test validation rejects negative expense amounts."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Try negative amount
        with pytest.raises(ValueError, match="must be positive"):
            service.record_expense(
                period_id=period.id,
                paid_by_user_id=users[0].id,
                amount=Decimal("-1000.00"),
                payment_type="Water",
                date_val=datetime.now()
            )

    def test_expense_validation_zero_amount(self, db_session, users):
        """Test validation rejects zero expense amounts."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Try zero amount
        with pytest.raises(ValueError, match="must be positive"):
            service.record_expense(
                period_id=period.id,
                paid_by_user_id=users[0].id,
                amount=Decimal("0.00"),
                payment_type="Water",
                date_val=datetime.now()
            )

    def test_expense_decimal_precision(self, db_session, users):
        """Test expense amounts maintain Decimal precision."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Test various high-precision amounts
        precision_amounts = [
            Decimal("1234.56"),
            Decimal("0.01"),
            Decimal("9999.99"),
            Decimal("5000.25"),
        ]
        
        for amount in precision_amounts:
            expense = service.record_expense(
                period_id=period.id,
                paid_by_user_id=users[0].id,
                amount=amount,
                payment_type="Water",
                date_val=datetime.now()
            )
            assert expense.amount == amount

    def test_expense_minimal_fields(self, db_session, users):
        """Test recording expense with only required fields."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record with minimal fields
        expense = service.record_expense(
            period_id=period.id,
            paid_by_user_id=users[0].id,
            amount=Decimal("500.00"),
            payment_type="Misc",
            date_val=datetime.now()
        )
        
        assert expense.id is not None
        assert expense.vendor is None
        assert expense.description is None
        assert expense.budget_item_id is None

    def test_expense_all_fields(self, db_session, users):
        """Test recording expense with all fields."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record with all fields
        expense = service.record_expense(
            period_id=period.id,
            paid_by_user_id=users[0].id,
            amount=Decimal("1500.00"),
            payment_type="Water & Sewer",
            date_val=datetime.now(),
            vendor="City Water Works",
            description="Q4 2025 billing cycle",
            budget_item_id=2
        )
        
        assert expense.vendor == "City Water Works"
        assert expense.description == "Q4 2025 billing cycle"
        assert expense.budget_item_id == 2
