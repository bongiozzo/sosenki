"""Integration tests for contribution workflows."""

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


class TestContributionWorkflows:
    """Test complete contribution management workflows."""

    def test_record_single_contribution(self, db_session, users):
        """Test recording a single contribution."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record contribution
        contribution = service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("500.00"),
            date_val=datetime.now(),
            comment="November payment"
        )
        
        assert contribution.id is not None
        assert contribution.amount == Decimal("500.00")
        assert contribution.user_id == users[0].id
        
        # Verify retrieval
        contributions = service.get_contributions(period.id)
        assert len(contributions) == 1
        assert contributions[0].id == contribution.id

    def test_record_multiple_contributions_same_owner(self, db_session, users):
        """Test recording multiple contributions from same owner."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record multiple contributions
        amounts = [Decimal("200.00"), Decimal("300.00"), Decimal("150.00")]
        
        for amount in amounts:
            service.record_contribution(
                period_id=period.id,
                user_id=users[0].id,
                amount=amount,
                date_val=datetime.now()
            )
        
        # Verify all recorded
        contributions = service.get_contributions(period.id)
        assert len(contributions) == 3
        
        # Verify cumulative
        total = service.get_owner_contributions(period.id, users[0].id)
        assert total == sum(amounts)

    def test_record_contributions_different_owners(self, db_session, users):
        """Test recording contributions from different owners."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record contributions from different owners
        contributions_data = [
            (users[0].id, Decimal("500.00")),
            (users[1].id, Decimal("600.00")),
            (users[2].id, Decimal("400.00")),
        ]
        
        for user_id, amount in contributions_data:
            service.record_contribution(
                period_id=period.id,
                user_id=user_id,
                amount=amount,
                date_val=datetime.now()
            )
        
        # Verify all recorded
        all_contributions = service.get_contributions(period.id)
        assert len(all_contributions) == 3
        
        # Verify individual totals
        for user_id, expected_amount in contributions_data:
            total = service.get_owner_contributions(period.id, user_id)
            assert total == expected_amount

    def test_contribution_chronological_ordering(self, db_session, users):
        """Test contributions are ordered chronologically."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record contributions with different dates
        dates = [
            datetime(2025, 11, 15, 10, 0),
            datetime(2025, 11, 10, 14, 30),
            datetime(2025, 11, 20, 9, 15),
        ]
        
        for date_val in dates:
            service.record_contribution(
                period_id=period.id,
                user_id=users[0].id,
                amount=Decimal("100.00"),
                date_val=date_val
            )
        
        # Retrieve and verify ordering
        contributions = service.get_contributions(period.id)
        retrieved_dates = [c.date for c in contributions]
        
        # Should be in chronological order
        assert retrieved_dates == sorted(retrieved_dates)

    def test_edit_contribution_amount(self, db_session, users):
        """Test editing contribution amount."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        contribution = service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("500.00"),
            date_val=datetime.now()
        )
        
        # Edit amount
        edited = service.edit_contribution(
            contribution.id,
            amount=Decimal("600.00")
        )
        
        assert edited.amount == Decimal("600.00")
        
        # Verify cumulative updated
        total = service.get_owner_contributions(period.id, users[0].id)
        assert total == Decimal("600.00")

    def test_edit_contribution_comment(self, db_session, users):
        """Test editing contribution comment."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        contribution = service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("500.00"),
            date_val=datetime.now(),
            comment="Initial comment"
        )
        
        # Edit comment
        edited = service.edit_contribution(
            contribution.id,
            comment="Updated comment"
        )
        
        assert edited.comment == "Updated comment"

    def test_contribution_history_for_owner(self, db_session, users):
        """Test retrieving contribution history for specific owner."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record contributions for multiple owners
        service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("200.00"),
            date_val=datetime.now()
        )
        service.record_contribution(
            period_id=period.id,
            user_id=users[1].id,
            amount=Decimal("300.00"),
            date_val=datetime.now()
        )
        service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("150.00"),
            date_val=datetime.now()
        )
        
        # Get user0 contributions via transaction history
        history = service.get_transaction_history(period.id, users[0].id)
        
        # Should only contain user0's contributions (not user1's)
        assert len(history) == 2

    def test_cannot_record_contribution_in_closed_period(self, db_session, users):
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
                period_id=period.id,
                user_id=users[0].id,
                amount=Decimal("500.00"),
                date_val=datetime.now()
            )

    def test_record_contribution_after_reopening_closed_period(self, db_session, users):
        """Test can record contribution after reopening closed period."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record initial contribution
        service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("500.00"),
            date_val=datetime.now()
        )
        
        # Close period
        service.close_period(period.id)
        
        # Reopen period
        service.reopen_period(period.id)
        
        # Should be able to record again
        service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("200.00"),
            date_val=datetime.now()
        )
        
        # Verify both recorded
        total = service.get_owner_contributions(period.id, users[0].id)
        assert total == Decimal("700.00")

    def test_contribution_validation_negative_amount(self, db_session, users):
        """Test validation rejects negative contribution amounts."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Try negative amount
        with pytest.raises(ValueError, match="must be positive"):
            service.record_contribution(
                period_id=period.id,
                user_id=users[0].id,
                amount=Decimal("-100.00"),
                date_val=datetime.now()
            )

    def test_contribution_validation_zero_amount(self, db_session, users):
        """Test validation rejects zero contribution amounts."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Try zero amount
        with pytest.raises(ValueError, match="must be positive"):
            service.record_contribution(
                period_id=period.id,
                user_id=users[0].id,
                amount=Decimal("0.00"),
                date_val=datetime.now()
            )

    def test_contribution_decimal_precision(self, db_session, users):
        """Test contribution amounts maintain Decimal precision."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Test various high-precision amounts
        precision_amounts = [
            Decimal("123.45"),
            Decimal("0.01"),
            Decimal("9999.99"),
            Decimal("1000.50"),
        ]
        
        for amount in precision_amounts:
            contribution = service.record_contribution(
                period_id=period.id,
                user_id=users[0].id,
                amount=amount,
                date_val=datetime.now()
            )
            assert contribution.amount == amount

    def test_contribution_cumulative_precision(self, db_session, users):
        """Test cumulative contributions maintain precision."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record contributions with precise amounts
        amounts = [
            Decimal("123.45"),
            Decimal("67.89"),
            Decimal("8.76"),
        ]
        
        for amount in amounts:
            service.record_contribution(
                period_id=period.id,
                user_id=users[0].id,
                amount=amount,
                date_val=datetime.now()
            )
        
        # Verify exact sum
        total = service.get_owner_contributions(period.id, users[0].id)
        expected = Decimal("200.10")
        assert total == expected

    def test_contribution_with_empty_comment(self, db_session, users):
        """Test recording contribution with empty comment."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record with empty string comment
        contribution = service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("500.00"),
            date_val=datetime.now(),
            comment=""
        )
        
        assert contribution.comment == ""

    def test_contribution_without_comment(self, db_session, users):
        """Test recording contribution without comment (None)."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record without comment
        contribution = service.record_contribution(
            period_id=period.id,
            user_id=users[0].id,
            amount=Decimal("500.00"),
            date_val=datetime.now()
        )
        
        assert contribution.comment is None
