"""Multi-period balance carry-forward tests (Phase 7b - T094-T102).

Tests for carrying balances between periods and applying opening balances.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, User, ServicePeriod, ContributionLedger, ExpenseLedger, ServiceCharge
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
    users_list = []
    for uid, tgid, username, name in users_data:
        user = User(id=uid, telegram_id=tgid, username=username, name=name)
        db_session.add(user)
        users_list.append(user)
    db_session.commit()
    return {
        "user1": users_list[0],
        "user2": users_list[1],
        "user3": users_list[2],
    }


class TestCarryForwardBalance:
    """T094: Carry-forward balance calculation between periods."""

    def test_carry_forward_positive_balance(self, db_session, users):
        """Test carrying forward a positive balance (credit)."""
        # Create first period
        period1 = ServicePeriod(
            name="Period 1",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            status="CLOSED"
        )
        db_session.add(period1)
        db_session.commit()

        # Record contribution: user1 pays 100
        contrib = ContributionLedger(
            service_period_id=period1.id,
            user_id=users["user1"].id,
            amount=Decimal("100.00"),
            date=datetime.now(),
        )
        db_session.add(contrib)
        db_session.commit()

        # Calculate balance (should be 100.00 credit)
        balance_svc = BalanceService(db_session)
        carried = balance_svc.carry_forward_balance(period1.id, 999)  # to_period_id not used

        assert users["user1"].id in carried
        assert carried[users["user1"].id] == Decimal("100.00")

    def test_carry_forward_negative_balance(self, db_session, users):
        """Test carrying forward a negative balance (debt)."""
        # Create period
        period1 = ServicePeriod(
            name="Period 1",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            status="CLOSED"
        )
        db_session.add(period1)
        db_session.commit()

        # Record charge: user1 owes 50
        charge = ServiceCharge(
            service_period_id=period1.id,
            user_id=users["user1"].id,
            description="Test charge",
            amount=Decimal("50.00")
        )
        db_session.add(charge)
        db_session.commit()

        # Calculate balance (should be -50.00 debt)
        balance_svc = BalanceService(db_session)
        carried = balance_svc.carry_forward_balance(period1.id, 999)

        assert users["user1"].id in carried
        assert carried[users["user1"].id] == Decimal("-50.00")

    def test_carry_forward_mixed_balances(self, db_session, users):
        """Test carrying forward multiple owners with different balances."""
        # Create period
        period1 = ServicePeriod(
            name="Period 1",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            status="CLOSED"
        )
        db_session.add(period1)
        db_session.commit()

        # user1: 100 contribution, no charges = +100 credit
        contrib1 = ContributionLedger(
            service_period_id=period1.id,
            user_id=users["user1"].id,
            amount=Decimal("100.00"),
            date=datetime.now(),
        )
        # user2: 50 contribution, 30 charge = +20 credit
        contrib2 = ContributionLedger(
            service_period_id=period1.id,
            user_id=users["user2"].id,
            amount=Decimal("50.00"),
            date=datetime.now(),
        )
        charge2 = ServiceCharge(
            service_period_id=period1.id,
            user_id=users["user2"].id,
            description="Test charge",
            amount=Decimal("30.00")
        )
        # user3: no contribution, 80 charge = -80 debt
        charge3 = ServiceCharge(
            service_period_id=period1.id,
            user_id=users["user3"].id,
            description="Test charge",
            amount=Decimal("80.00")
        )
        db_session.add_all([contrib1, contrib2, charge2, charge3])
        db_session.commit()

        balance_svc = BalanceService(db_session)
        carried = balance_svc.carry_forward_balance(period1.id, 999)

        assert carried[users["user1"].id] == Decimal("100.00")
        assert carried[users["user2"].id] == Decimal("20.00")
        assert carried[users["user3"].id] == Decimal("-80.00")

    def test_carry_forward_zero_balance_not_included(self, db_session, users):
        """Test that zero balances are not carried forward."""
        period1 = ServicePeriod(
            name="Period 1",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            status="CLOSED"
        )
        db_session.add(period1)
        db_session.commit()

        # user1: 100 contribution, 100 charge = 0 balance
        contrib = ContributionLedger(
            service_period_id=period1.id,
            user_id=users["user1"].id,
            amount=Decimal("100.00"),
            date=datetime.now(),
        )
        charge = ServiceCharge(
            service_period_id=period1.id,
            user_id=users["user1"].id,
            description="Test charge",
            amount=Decimal("100.00")
        )
        db_session.add_all([contrib, charge])
        db_session.commit()

        balance_svc = BalanceService(db_session)
        carried = balance_svc.carry_forward_balance(period1.id, 999)

        # Should not include user1 since balance is zero
        assert users["user1"].id not in carried

    def test_carry_forward_empty_period(self, db_session):
        """Test carrying forward from empty period."""
        period1 = ServicePeriod(
            name="Period 1",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            status="CLOSED"
        )
        db_session.add(period1)
        db_session.commit()

        balance_svc = BalanceService(db_session)
        carried = balance_svc.carry_forward_balance(period1.id, 999)

        assert carried == {}


class TestApplyOpeningBalance:
    """T095: Apply opening balances to new period."""

    def test_apply_positive_opening_balance(self, db_session, users):
        """Test applying positive opening balance as contribution."""
        # Create new period
        period2 = ServicePeriod(
            name="Period 2",
            start_date=datetime.now() + timedelta(days=31),
            end_date=datetime.now() + timedelta(days=61),
            status="OPEN"
        )
        db_session.add(period2)
        db_session.commit()

        # Apply opening balance
        balance_svc = BalanceService(db_session)
        opening = {users["user1"].id: Decimal("100.00")}
        balance_svc.apply_opening_balance(period2.id, opening)

        # Verify opening contribution was created
        contrib = db_session.query(ContributionLedger).filter(
            ContributionLedger.service_period_id == period2.id,
            ContributionLedger.user_id == users["user1"].id
        ).first()

        assert contrib is not None
        assert contrib.amount == Decimal("100.00")
        assert "Opening balance" in contrib.comment

    def test_apply_negative_opening_balance(self, db_session, users):
        """Test applying negative opening balance as charge."""
        # Create new period
        period2 = ServicePeriod(
            name="Period 2",
            start_date=datetime.now() + timedelta(days=31),
            end_date=datetime.now() + timedelta(days=61),
            status="OPEN"
        )
        db_session.add(period2)
        db_session.commit()

        # Apply opening balance (negative = debt)
        balance_svc = BalanceService(db_session)
        opening = {users["user1"].id: Decimal("-80.00")}
        balance_svc.apply_opening_balance(period2.id, opening)

        # Verify opening charge was created
        charge = db_session.query(ServiceCharge).filter(
            ServiceCharge.service_period_id == period2.id,
            ServiceCharge.user_id == users["user1"].id
        ).first()

        assert charge is not None
        assert charge.amount == Decimal("80.00")
        assert "Opening debt" in charge.description

    def test_apply_mixed_opening_balances(self, db_session, users):
        """Test applying mixed positive and negative opening balances."""
        # Create new period
        period2 = ServicePeriod(
            name="Period 2",
            start_date=datetime.now() + timedelta(days=31),
            end_date=datetime.now() + timedelta(days=61),
            status="OPEN"
        )
        db_session.add(period2)
        db_session.commit()

        # Apply opening balances
        balance_svc = BalanceService(db_session)
        opening = {
            users["user1"].id: Decimal("100.00"),  # credit
            users["user2"].id: Decimal("-50.00"),  # debt
            users["user3"].id: Decimal("0.00"),    # zero
        }
        balance_svc.apply_opening_balance(period2.id, opening)

        # Verify contributions and charges
        contrib = db_session.query(ContributionLedger).filter(
            ContributionLedger.service_period_id == period2.id,
            ContributionLedger.user_id == users["user1"].id
        ).first()
        assert contrib is not None
        assert contrib.amount == Decimal("100.00")

        charge = db_session.query(ServiceCharge).filter(
            ServiceCharge.service_period_id == period2.id,
            ServiceCharge.user_id == users["user2"].id
        ).first()
        assert charge is not None
        assert charge.amount == Decimal("50.00")

        # Verify user3 has no opening transactions (zero balance)
        user3_transactions = db_session.query(ContributionLedger).filter(
            ContributionLedger.service_period_id == period2.id,
            ContributionLedger.user_id == users["user3"].id
        ).all()
        user3_charges = db_session.query(ServiceCharge).filter(
            ServiceCharge.service_period_id == period2.id,
            ServiceCharge.user_id == users["user3"].id
        ).all()
        assert len(user3_transactions) == 0
        assert len(user3_charges) == 0

    def test_apply_zero_opening_balance(self, db_session, users):
        """Test that zero opening balances create no transactions."""
        period2 = ServicePeriod(
            name="Period 2",
            start_date=datetime.now() + timedelta(days=31),
            end_date=datetime.now() + timedelta(days=61),
            status="OPEN"
        )
        db_session.add(period2)
        db_session.commit()

        balance_svc = BalanceService(db_session)
        opening = {users["user1"].id: Decimal("0.00")}
        balance_svc.apply_opening_balance(period2.id, opening)

        # Verify no transactions created
        contrib = db_session.query(ContributionLedger).filter(
            ContributionLedger.service_period_id == period2.id,
            ContributionLedger.user_id == users["user1"].id
        ).first()
        charge = db_session.query(ServiceCharge).filter(
            ServiceCharge.service_period_id == period2.id,
            ServiceCharge.user_id == users["user1"].id
        ).first()

        assert contrib is None
        assert charge is None


class TestMultiPeriodReconciliation:
    """T100-T101: Multi-period balance reconciliation."""

    def test_balance_carry_forward_accuracy(self, db_session, users):
        """T101: Test accuracy of balance carry-forward."""
        # Create period 1
        period1 = ServicePeriod(
            name="Period 1",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            status="CLOSED"
        )
        db_session.add(period1)
        db_session.commit()

        # Setup: user1 has complex balance
        # Contributions: 500.00, 250.00 = 750.00
        # Charges: 200.00
        # Expected balance: 550.00
        contrib1 = ContributionLedger(
            service_period_id=period1.id,
            user_id=users["user1"].id,
            amount=Decimal("500.00"),
            date=datetime.now(),
        )
        contrib2 = ContributionLedger(
            service_period_id=period1.id,
            user_id=users["user1"].id,
            amount=Decimal("250.00"),
            date=datetime.now() + timedelta(days=5),
        )
        charge = ServiceCharge(
            service_period_id=period1.id,
            user_id=users["user1"].id,
            description="Service charge",
            amount=Decimal("200.00")
        )
        db_session.add_all([contrib1, contrib2, charge])
        db_session.commit()

        # Calculate balance from period 1
        balance_svc = BalanceService(db_session)
        period1_balance = balance_svc.get_owner_balance(period1.id, users["user1"].id)
        assert period1_balance == Decimal("550.00")

        # Create period 2
        period2 = ServicePeriod(
            name="Period 2",
            start_date=datetime.now() + timedelta(days=31),
            end_date=datetime.now() + timedelta(days=61),
            status="OPEN"
        )
        db_session.add(period2)
        db_session.commit()

        # Carry forward balance
        carried = balance_svc.carry_forward_balance(period1.id, period2.id)
        assert carried[users["user1"].id] == Decimal("550.00")

        # Apply to period 2
        balance_svc.apply_opening_balance(period2.id, carried)

        # Verify period 2 starts with same balance
        period2_balance = balance_svc.get_owner_balance(period2.id, users["user1"].id)
        assert period2_balance == Decimal("550.00")

    def test_multi_period_balance_chain(self, db_session, users):
        """Test balance chain across 3 periods."""
        balance_svc = BalanceService(db_session)

        # Period 1: start with 100.00
        period1 = ServicePeriod(
            name="Period 1",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            status="CLOSED"
        )
        db_session.add(period1)
        db_session.commit()

        contrib1 = ContributionLedger(
            service_period_id=period1.id,
            user_id=users["user1"].id,
            amount=Decimal("100.00"),
            date=datetime.now(),
        )
        db_session.add(contrib1)
        db_session.commit()

        # Carry to period 2
        period2 = ServicePeriod(
            name="Period 2",
            start_date=datetime.now() + timedelta(days=31),
            end_date=datetime.now() + timedelta(days=61),
            status="CLOSED"
        )
        db_session.add(period2)
        db_session.commit()

        carried1 = balance_svc.carry_forward_balance(period1.id, period2.id)
        balance_svc.apply_opening_balance(period2.id, carried1)

        # Add 50 in period 2
        contrib2 = ContributionLedger(
            service_period_id=period2.id,
            user_id=users["user1"].id,
            amount=Decimal("50.00"),
            date=datetime.now() + timedelta(days=31),
        )
        db_session.add(contrib2)
        db_session.commit()

        # Period 2 balance should be 150
        period2_balance = balance_svc.get_owner_balance(period2.id, users["user1"].id)
        assert period2_balance == Decimal("150.00")

        # Carry to period 3
        period3 = ServicePeriod(
            name="Period 3",
            start_date=datetime.now() + timedelta(days=62),
            end_date=datetime.now() + timedelta(days=92),
            status="OPEN"
        )
        db_session.add(period3)
        db_session.commit()

        carried2 = balance_svc.carry_forward_balance(period2.id, period3.id)
        balance_svc.apply_opening_balance(period3.id, carried2)

        # Period 3 should start with 150
        period3_balance = balance_svc.get_owner_balance(period3.id, users["user1"].id)
        assert period3_balance == Decimal("150.00")

    def test_zero_balance_not_carried(self, db_session, users):
        """Test that zero balances don't create clutter in carry-forward."""
        balance_svc = BalanceService(db_session)

        # Period 1: balanced (100 in, 100 out)
        period1 = ServicePeriod(
            name="Period 1",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            status="CLOSED"
        )
        db_session.add(period1)
        db_session.commit()

        contrib = ContributionLedger(
            service_period_id=period1.id,
            user_id=users["user1"].id,
            amount=Decimal("100.00"),
            date=datetime.now(),
        )
        charge = ServiceCharge(
            service_period_id=period1.id,
            user_id=users["user1"].id,
            description="Charge",
            amount=Decimal("100.00")
        )
        db_session.add_all([contrib, charge])
        db_session.commit()

        # Carry forward
        period2 = ServicePeriod(
            name="Period 2",
            start_date=datetime.now() + timedelta(days=31),
            end_date=datetime.now() + timedelta(days=61),
            status="OPEN"
        )
        db_session.add(period2)
        db_session.commit()

        carried = balance_svc.carry_forward_balance(period1.id, period2.id)
        assert users["user1"].id not in carried
        assert len(carried) == 0

        balance_svc.apply_opening_balance(period2.id, carried)

        # Period 2 should have zero balance (no opening transactions)
        period2_balance = balance_svc.get_owner_balance(period2.id, users["user1"].id)
        assert period2_balance == Decimal("0.00")


class TestBalanceValidation:
    """T096: Balance validation - sum of allocations = total expenses (no money loss)."""

    def test_period_total_balance_zero(self, db_session, users):
        """Test that total period balance equals zero (money in = money out)."""
        period = ServicePeriod(
            name="Period",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            status="CLOSED"
        )
        db_session.add(period)
        db_session.commit()

        # Total in: 300 (user1: 100, user2: 200)
        contrib1 = ContributionLedger(
            service_period_id=period.id,
            user_id=users["user1"].id,
            amount=Decimal("100.00"),
            date=datetime.now(),
        )
        contrib2 = ContributionLedger(
            service_period_id=period.id,
            user_id=users["user2"].id,
            amount=Decimal("200.00"),
            date=datetime.now(),
        )
        # Total out: 300 in charges
        charge1 = ServiceCharge(
            service_period_id=period.id,
            user_id=users["user1"].id,
            description="Charge",
            amount=Decimal("150.00")
        )
        charge2 = ServiceCharge(
            service_period_id=period.id,
            user_id=users["user2"].id,
            description="Charge",
            amount=Decimal("150.00")
        )
        db_session.add_all([contrib1, contrib2, charge1, charge2])
        db_session.commit()

        balance_svc = BalanceService(db_session)
        total_balance = balance_svc.get_period_total_balance(period.id)

        # Total should be zero (balanced)
        assert total_balance == Decimal("0.00")

    def test_period_balance_with_surplus(self, db_session, users):
        """Test period balance when there's surplus (more in than out)."""
        period = ServicePeriod(
            name="Period",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            status="CLOSED"
        )
        db_session.add(period)
        db_session.commit()

        # Total in: 500
        contrib = ContributionLedger(
            service_period_id=period.id,
            user_id=users["user1"].id,
            amount=Decimal("500.00"),
            date=datetime.now(),
        )
        # Total out: 300
        charge = ServiceCharge(
            service_period_id=period.id,
            user_id=users["user2"].id,
            description="Charge",
            amount=Decimal("300.00")
        )
        db_session.add_all([contrib, charge])
        db_session.commit()

        balance_svc = BalanceService(db_session)
        total_balance = balance_svc.get_period_total_balance(period.id)

        # user1 has 500 credit, user2 has -300 debt = 200 total surplus
        assert total_balance == Decimal("200.00")

    def test_fractional_allocations_accuracy(self, db_session, users):
        """Test that fractional allocations maintain cent-level precision."""
        period = ServicePeriod(
            name="Period",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            status="CLOSED"
        )
        db_session.add(period)
        db_session.commit()

        # Contributions with fractional amounts
        contrib1 = ContributionLedger(
            service_period_id=period.id,
            user_id=users["user1"].id,
            amount=Decimal("100.33"),
            date=datetime.now(),
        )
        contrib2 = ContributionLedger(
            service_period_id=period.id,
            user_id=users["user2"].id,
            amount=Decimal("200.67"),
            date=datetime.now(),
        )
        contrib3 = ContributionLedger(
            service_period_id=period.id,
            user_id=users["user3"].id,
            amount=Decimal("50.17"),
            date=datetime.now(),
        )
        # Charges with fractional amounts
        charge1 = ServiceCharge(
            service_period_id=period.id,
            user_id=users["user1"].id,
            description="Charge",
            amount=Decimal("75.49")
        )
        charge2 = ServiceCharge(
            service_period_id=period.id,
            user_id=users["user2"].id,
            description="Charge",
            amount=Decimal("120.68")
        )
        db_session.add_all([contrib1, contrib2, contrib3, charge1, charge2])
        db_session.commit()

        balance_svc = BalanceService(db_session)

        # Verify each balance is accurate to the cent
        assert balance_svc.get_owner_balance(period.id, users["user1"].id) == Decimal("24.84")
        assert balance_svc.get_owner_balance(period.id, users["user2"].id) == Decimal("79.99")
        assert balance_svc.get_owner_balance(period.id, users["user3"].id) == Decimal("50.17")

        # Total should equal sum of individual balances
        total = balance_svc.get_period_total_balance(period.id)
        assert total == Decimal("155.00")
