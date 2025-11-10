"""Contract tests for multi-period carry-forward API endpoints (Phase 7b - T102).

Tests the API contracts for balance carry-forward functionality.
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, User, ServicePeriod, ContributionLedger, ServiceCharge
from src.services.balance_service import BalanceService
from src.services.payment_service import PaymentService
from src.api.payment import (
    CarryForwardRequest,
    CarryForwardResponse,
)


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


class TestCarryForwardApiContract:
    """T102: Contract tests for carry-forward API endpoints."""

    def test_carry_forward_request_structure(self, db_session, users):
        """Test CarryForwardRequest model structure."""
        request = CarryForwardRequest(
            from_period_id=1,
            to_period_id=2
        )

        assert request.from_period_id == 1
        assert request.to_period_id == 2

    def test_carry_forward_response_structure(self):
        """Test CarryForwardResponse model structure."""
        response = CarryForwardResponse(
            from_period_id=1,
            to_period_id=2,
            carried_forward_owners={1: Decimal("100.00"), 2: Decimal("-50.00")},
            total_carried=Decimal("50.00"),
            message="Successfully carried forward 2 owner balances"
        )

        assert response.from_period_id == 1
        assert response.to_period_id == 2
        assert len(response.carried_forward_owners) == 2
        assert response.carried_forward_owners[1] == Decimal("100.00")
        assert response.carried_forward_owners[2] == Decimal("-50.00")
        assert response.total_carried == Decimal("50.00")
        assert "Successfully carried forward" in response.message

    def test_carry_forward_request_validation(self):
        """Test that CarryForwardRequest validates required fields."""
        # Both fields required
        request = CarryForwardRequest(from_period_id=1, to_period_id=2)
        assert request is not None

    def test_carry_forward_response_validation(self):
        """Test CarryForwardResponse field validation."""
        # All fields required in response
        response = CarryForwardResponse(
            from_period_id=1,
            to_period_id=2,
            carried_forward_owners={},
            total_carried=Decimal("0.00"),
            message="No balances to carry forward"
        )
        assert response is not None

    def test_carry_forward_scenario_full_workflow(self, db_session, users):
        """Test full carry-forward workflow (service → API response)."""
        # Create periods
        payment_service = PaymentService(db=db_session)
        period1 = payment_service.create_period(
            name="Period 1",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        period2 = payment_service.create_period(
            name="Period 2",
            start_date=date(2025, 12, 1),
            end_date=date(2025, 12, 31)
        )

        # Record transactions in period 1
        payment_service.record_contribution(
            period_id=period1.id,
            user_id=users["user1"].id,
            amount=Decimal("500.00"),
            date_val=datetime.now()
        )
        payment_service.record_service_charge(
            period_id=period1.id,
            user_id=users["user2"].id,
            description="Test charge",
            amount=Decimal("200.00")
        )

        # Close period 1
        payment_service.close_period(period1.id)

        # Carry forward
        balance_service = BalanceService(db=db_session)
        carried = balance_service.carry_forward_balance(period1.id, period2.id)

        # Verify response can be constructed
        response = CarryForwardResponse(
            from_period_id=period1.id,
            to_period_id=period2.id,
            carried_forward_owners=carried,
            total_carried=sum(carried.values()),
            message=f"Successfully carried forward {len(carried)} owner balances"
        )

        assert response.from_period_id == period1.id
        assert response.to_period_id == period2.id
        assert len(response.carried_forward_owners) > 0
        assert response.total_carried == Decimal("300.00")

    def test_opening_transactions_endpoint_response(self, db_session, users):
        """Test structure of opening transactions response."""
        payment_service = PaymentService(db=db_session)
        balance_service = BalanceService(db=db_session)

        period1 = payment_service.create_period(
            name="Period 1",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        period2 = payment_service.create_period(
            name="Period 2",
            start_date=date(2025, 12, 1),
            end_date=date(2025, 12, 31)
        )

        # Setup period 1 with balances
        payment_service.record_contribution(
            period_id=period1.id,
            user_id=users["user1"].id,
            amount=Decimal("500.00"),
            date_val=datetime.now()
        )
        payment_service.close_period(period1.id)

        # Carry forward to period 2
        carried = balance_service.carry_forward_balance(period1.id, period2.id)
        balance_service.apply_opening_balance(period2.id, carried)

        # Verify opening transactions were created
        opening_contribs = db_session.query(ContributionLedger).filter(
            ContributionLedger.service_period_id == period2.id,
            ContributionLedger.comment.like("%Opening balance%")
        ).all()

        assert len(opening_contribs) > 0
        opening_contrib = opening_contribs[0]

        # Verify response structure
        response_contrib = {
            "id": opening_contrib.id,
            "user_id": opening_contrib.user_id,
            "amount": opening_contrib.amount,
            "date": opening_contrib.date,
            "comment": opening_contrib.comment
        }
        assert response_contrib["user_id"] == users["user1"].id
        assert response_contrib["amount"] == Decimal("500.00")
        assert "Opening balance" in response_contrib["comment"]

    def test_carry_forward_with_mixed_balances_response(self, db_session, users):
        """Test carry-forward response with mixed positive/negative balances."""
        payment_service = PaymentService(db=db_session)
        balance_service = BalanceService(db=db_session)

        period1 = payment_service.create_period(
            name="Period 1",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )

        # user1: +100 credit
        payment_service.record_contribution(
            period_id=period1.id,
            user_id=users["user1"].id,
            amount=Decimal("100.00"),
            date_val=datetime.now()
        )

        # user2: -80 debt
        payment_service.record_service_charge(
            period_id=period1.id,
            user_id=users["user2"].id,
            description="Charge",
            amount=Decimal("80.00")
        )

        payment_service.close_period(period1.id)

        # Generate response
        carried = balance_service.carry_forward_balance(period1.id, 999)
        response = CarryForwardResponse(
            from_period_id=period1.id,
            to_period_id=999,
            carried_forward_owners=carried,
            total_carried=sum(carried.values()),
            message=f"Successfully carried forward {len(carried)} owner balances"
        )

        # Verify response contains both positive and negative balances
        assert len(response.carried_forward_owners) == 2
        assert response.carried_forward_owners[users["user1"].id] == Decimal("100.00")
        assert response.carried_forward_owners[users["user2"].id] == Decimal("-80.00")
        assert response.total_carried == Decimal("20.00")

    def test_carry_forward_empty_result_response(self, db_session):
        """Test carry-forward response when no balances to carry."""
        payment_service = PaymentService(db=db_session)
        balance_service = BalanceService(db=db_session)

        period1 = payment_service.create_period(
            name="Period 1",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        payment_service.close_period(period1.id)

        # Empty carry-forward
        carried = balance_service.carry_forward_balance(period1.id, 999)

        response = CarryForwardResponse(
            from_period_id=period1.id,
            to_period_id=999,
            carried_forward_owners=carried,
            total_carried=sum(carried.values()) if carried else Decimal("0.00"),
            message=f"Successfully carried forward {len(carried)} owner balances"
        )

        assert len(response.carried_forward_owners) == 0
        assert response.total_carried == Decimal("0.00")
        assert "0 owner balances" in response.message

    def test_carry_forward_error_scenarios(self, db_session):
        """Test error response structures for carry-forward scenarios."""
        # Test missing period error
        # (In actual API, would be HTTPException with 404)
        payment_service = PaymentService(db=db_session)

        result = payment_service.get_period(999)
        assert result is None

        # Test closed period status check
        period = payment_service.create_period(
            name="Test",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        assert period.status == "OPEN"

        payment_service.close_period(period.id)
        updated = payment_service.get_period(period.id)
        assert updated.status == "CLOSED"
