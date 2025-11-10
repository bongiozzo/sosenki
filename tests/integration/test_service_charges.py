"""Integration tests for service charge management."""

import pytest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, User, PeriodStatus
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
    """Create test users."""
    users_data = [(1, 12345, "alice", "Alice User"), (2, 12346, "bob", "Bob User"), (3, 12347, "charlie", "Charlie User")]
    users = []
    for uid, tgid, username, name in users_data:
        user = User(id=uid, telegram_id=tgid, username=username, name=name)
        db_session.add(user)
        users.append(user)
    db_session.commit()
    return users


class TestServiceChargeManagement:
    """Test service charge CRUD operations."""

    def test_record_service_charge(self, db_session, users):
        """Test recording a service charge."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        charge = service.record_service_charge(
            period_id=period.id,
            user_id=users[0].id,
            description="Maintenance fee",
            amount=Decimal("500.00")
        )
        
        assert charge.id is not None
        assert charge.service_period_id == period.id
        assert charge.user_id == users[0].id
        assert charge.description == "Maintenance fee"
        assert charge.amount == Decimal("500.00")

    def test_record_multiple_charges_same_owner(self, db_session, users):
        """Test recording multiple charges for the same owner."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record multiple charges
        for i in range(3):
            service.record_service_charge(
                period_id=period.id,
                user_id=users[0].id,
                description=f"Charge {i+1}",
                amount=Decimal("100.00")
            )
        
        charges = service.get_owner_service_charges(period.id, users[0].id)
        assert len(charges) == 3

    def test_get_service_charge(self, db_session, users):
        """Test retrieving a specific service charge."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        created = service.record_service_charge(
            period_id=period.id,
            user_id=users[0].id,
            description="Maintenance fee",
            amount=Decimal("500.00")
        )
        
        retrieved = service.get_service_charge(created.id)
        assert retrieved.id == created.id
        assert retrieved.description == "Maintenance fee"
        assert retrieved.amount == Decimal("500.00")

    def test_get_all_period_charges(self, db_session, users):
        """Test retrieving all charges for a period."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record charges for different owners
        for i, user in enumerate(users):
            service.record_service_charge(
                period_id=period.id,
                user_id=user.id,
                description=f"Charge for {user.username}",
                amount=Decimal("100.00") * (i + 1)
            )
        
        all_charges = service.get_service_charges(period.id)
        assert len(all_charges) == 3

    def test_update_service_charge(self, db_session, users):
        """Test updating a service charge."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        charge = service.record_service_charge(
            period_id=period.id,
            user_id=users[0].id,
            description="Initial charge",
            amount=Decimal("500.00")
        )
        
        # Update description and amount
        updated = service.update_service_charge(
            charge.id,
            description="Updated maintenance fee",
            amount=Decimal("750.00")
        )
        
        assert updated.description == "Updated maintenance fee"
        assert updated.amount == Decimal("750.00")

    def test_update_service_charge_partial(self, db_session, users):
        """Test partial update of service charge."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        charge = service.record_service_charge(
            period_id=period.id,
            user_id=users[0].id,
            description="Original",
            amount=Decimal("500.00")
        )
        
        # Update only amount
        updated = service.update_service_charge(
            charge.id,
            amount=Decimal("600.00")
        )
        
        assert updated.description == "Original"  # Unchanged
        assert updated.amount == Decimal("600.00")  # Changed

    def test_delete_service_charge(self, db_session, users):
        """Test deleting a service charge."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        charge = service.record_service_charge(
            period_id=period.id,
            user_id=users[0].id,
            description="Temporary charge",
            amount=Decimal("500.00")
        )
        
        # Delete it
        deleted = service.delete_service_charge(charge.id)
        assert deleted is True
        
        # Verify it's deleted
        retrieved = service.get_service_charge(charge.id)
        assert retrieved is None

    def test_service_charge_validation_negative_amount(self, db_session, users):
        """Test validation rejects negative amounts."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        with pytest.raises(ValueError, match="must be positive"):
            service.record_service_charge(
                period_id=period.id,
                user_id=users[0].id,
                description="Invalid charge",
                amount=Decimal("-500.00")
            )

    def test_service_charge_validation_zero_amount(self, db_session, users):
        """Test validation rejects zero amounts."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        with pytest.raises(ValueError, match="must be positive"):
            service.record_service_charge(
                period_id=period.id,
                user_id=users[0].id,
                description="Invalid charge",
                amount=Decimal("0.00")
            )

    def test_service_charge_on_closed_period(self, db_session, users):
        """Test cannot record charge on closed period."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Close the period
        service.close_period(period.id)
        
        with pytest.raises(ValueError, match="not open"):
            service.record_service_charge(
                period_id=period.id,
                user_id=users[0].id,
                description="Charge on closed period",
                amount=Decimal("500.00")
            )

    def test_update_charge_on_closed_period(self, db_session, users):
        """Test cannot update charge when period is closed."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        charge = service.record_service_charge(
            period_id=period.id,
            user_id=users[0].id,
            description="Charge",
            amount=Decimal("500.00")
        )
        
        # Close the period
        service.close_period(period.id)
        
        with pytest.raises(ValueError, match="not open"):
            service.update_service_charge(
                charge.id,
                amount=Decimal("600.00")
            )

    def test_owner_charge_summary(self, db_session, users):
        """Test getting charge summary for owner."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record multiple charges for first user
        amounts = [Decimal("100.00"), Decimal("200.00"), Decimal("150.00")]
        for amount in amounts:
            service.record_service_charge(
                period_id=period.id,
                user_id=users[0].id,
                description=f"Charge {amount}",
                amount=amount
            )
        
        charges = service.get_owner_service_charges(period.id, users[0].id)
        total = sum(c.amount for c in charges)
        
        assert len(charges) == 3
        assert total == Decimal("450.00")

    def test_invalid_charge_id(self, db_session):
        """Test retrieving non-existent charge returns None."""
        service = PaymentService(db=db_session)
        
        charge = service.get_service_charge(9999)
        assert charge is None

    def test_delete_nonexistent_charge(self, db_session):
        """Test deleting non-existent charge returns False."""
        service = PaymentService(db=db_session)
        
        deleted = service.delete_service_charge(9999)
        assert deleted is False
