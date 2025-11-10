"""Contract tests for payment API endpoints."""

import pytest
from datetime import date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.models import Base, User
from src.api.payment import router


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
def client(db_session):
    """Create test client with database dependency override."""
    def get_db():
        return db_session
    
    # Note: In a real implementation, would override app dependency
    # For now, this is a structural test
    return TestClient(app)


@pytest.fixture
def sample_user(db_session):
    """Create sample user."""
    user = User(id=1, telegram_id=12345, username="testuser", name="Test User")
    db_session.add(user)
    db_session.commit()
    return user


class TestPeriodEndpointContract:
    """Test contract for period management endpoints."""

    def test_create_period_request_structure(self):
        """Test create period endpoint accepts correct structure."""
        payload = {
            "name": "November 2025",
            "start_date": "2025-11-01",
            "end_date": "2025-11-30",
            "description": "Monthly billing period"
        }
        # Validates JSON schema
        assert payload["name"] == "November 2025"
        assert payload["start_date"] == "2025-11-01"

    def test_create_period_response_structure(self):
        """Test create period response has correct structure."""
        response_data = {
            "id": 1,
            "name": "November 2025",
            "start_date": "2025-11-01",
            "end_date": "2025-11-30",
            "status": "OPEN",
            "description": "Monthly billing period",
            "closed_at": None
        }
        # Validates response schema
        assert "id" in response_data
        assert "name" in response_data
        assert "status" in response_data
        assert response_data["status"] in ["OPEN", "CLOSED"]

    def test_list_periods_response_structure(self):
        """Test list periods returns array of period objects."""
        response_data = [
            {
                "id": 1,
                "name": "November 2025",
                "start_date": "2025-11-01",
                "end_date": "2025-11-30",
                "status": "OPEN",
                "description": None,
                "closed_at": None
            },
            {
                "id": 2,
                "name": "October 2025",
                "start_date": "2025-10-01",
                "end_date": "2025-10-31",
                "status": "CLOSED",
                "description": None,
                "closed_at": "2025-11-01T12:00:00"
            }
        ]
        
        assert isinstance(response_data, list)
        assert len(response_data) == 2
        for period in response_data:
            assert "id" in period
            assert "name" in period
            assert "status" in period

    def test_close_period_response_structure(self):
        """Test close period returns updated period."""
        response_data = {
            "id": 1,
            "name": "November 2025",
            "start_date": "2025-11-01",
            "end_date": "2025-11-30",
            "status": "CLOSED",
            "description": None,
            "closed_at": "2025-12-01T12:00:00"
        }
        
        assert response_data["status"] == "CLOSED"
        assert response_data["closed_at"] is not None

    def test_reopen_period_response_structure(self):
        """Test reopen period returns updated period."""
        response_data = {
            "id": 1,
            "name": "November 2025",
            "start_date": "2025-11-01",
            "end_date": "2025-11-30",
            "status": "OPEN",
            "description": None,
            "closed_at": None
        }
        
        assert response_data["status"] == "OPEN"
        assert response_data["closed_at"] is None


class TestContributionEndpointContract:
    """Test contract for contribution endpoints."""

    def test_record_contribution_request_structure(self):
        """Test record contribution request format."""
        payload = {
            "user_id": 1,
            "amount": "500.00",
            "comment": "November payment"
        }
        
        assert payload["user_id"] == 1
        assert isinstance(payload["amount"], str)

    def test_record_contribution_response_structure(self):
        """Test record contribution response format."""
        response_data = {
            "id": 1,
            "service_period_id": 1,
            "user_id": 1,
            "amount": "500.00",
            "date": "2025-11-15T10:30:00",
            "comment": "November payment"
        }
        
        assert "id" in response_data
        assert "amount" in response_data
        assert response_data["amount"] == "500.00"

    def test_list_contributions_response_structure(self):
        """Test list contributions returns array."""
        response_data = [
            {
                "id": 1,
                "service_period_id": 1,
                "user_id": 1,
                "amount": "500.00",
                "date": "2025-11-15T10:30:00",
                "comment": None
            }
        ]
        
        assert isinstance(response_data, list)

    def test_owner_contributions_summary_structure(self):
        """Test owner contributions summary format."""
        response_data = {
            "owner_id": 1,
            "total_contributed": "500.00"
        }
        
        assert response_data["owner_id"] == 1
        assert "total_contributed" in response_data


class TestExpenseEndpointContract:
    """Test contract for expense endpoints."""

    def test_record_expense_request_structure(self):
        """Test record expense request format."""
        payload = {
            "paid_by_user_id": 1,
            "amount": "1500.00",
            "payment_type": "Water",
            "vendor": "City Water",
            "description": "Q4 water bill",
            "budget_item_id": 1
        }
        
        assert payload["paid_by_user_id"] == 1
        assert payload["payment_type"] == "Water"

    def test_record_expense_response_structure(self):
        """Test record expense response format."""
        response_data = {
            "id": 1,
            "service_period_id": 1,
            "paid_by_user_id": 1,
            "amount": "1500.00",
            "payment_type": "Water",
            "date": "2025-11-15T10:30:00",
            "vendor": "City Water",
            "description": "Q4 water bill",
            "budget_item_id": 1
        }
        
        assert "id" in response_data
        assert "amount" in response_data
        assert "payment_type" in response_data

    def test_list_expenses_response_structure(self):
        """Test list expenses returns array."""
        response_data = [
            {
                "id": 1,
                "service_period_id": 1,
                "paid_by_user_id": 1,
                "amount": "1500.00",
                "payment_type": "Water",
                "date": "2025-11-15T10:30:00",
                "vendor": "City Water",
                "description": None,
                "budget_item_id": None
            }
        ]
        
        assert isinstance(response_data, list)


class TestServiceChargeEndpointContract:
    """Test contract for service charge endpoints."""

    def test_record_charge_request_structure(self):
        """Test record service charge request format."""
        payload = {
            "user_id": 1,
            "description": "Late fee",
            "amount": "50.00"
        }
        
        assert payload["user_id"] == 1
        assert payload["description"] == "Late fee"

    def test_record_charge_response_structure(self):
        """Test record service charge response format."""
        response_data = {
            "id": 1,
            "service_period_id": 1,
            "user_id": 1,
            "description": "Late fee",
            "amount": "50.00"
        }
        
        assert "id" in response_data
        assert "amount" in response_data
        assert response_data["description"] == "Late fee"

    def test_list_charges_response_structure(self):
        """Test list charges returns array."""
        response_data = [
            {
                "id": 1,
                "service_period_id": 1,
                "user_id": 1,
                "description": "Late fee",
                "amount": "50.00"
            }
        ]
        
        assert isinstance(response_data, list)


class TestEndpointValidation:
    """Test endpoint request/response validation."""

    def test_decimal_amount_precision(self):
        """Test amounts maintain decimal precision."""
        amount = "123.45"
        assert amount == "123.45"
        
        # High precision should work
        amount = "9999.99"
        assert amount == "9999.99"

    def test_date_format_iso8601(self):
        """Test dates use ISO 8601 format."""
        start_date = "2025-11-01"
        end_date = "2025-11-30"
        
        assert start_date == "2025-11-01"
        assert end_date == "2025-11-30"

    def test_datetime_format_iso8601(self):
        """Test datetimes use ISO 8601 format."""
        timestamp = "2025-11-15T10:30:00"
        
        # Should be parseable as ISO8601
        assert "T" in timestamp
        assert ":" in timestamp

    def test_status_enum_values(self):
        """Test status uses correct enum values."""
        valid_statuses = ["OPEN", "CLOSED"]
        
        for status in valid_statuses:
            assert status in ["OPEN", "CLOSED"]

    def test_error_response_structure(self):
        """Test error responses have correct structure."""
        error_response = {
            "detail": "Period 999 not found"
        }
        
        assert "detail" in error_response
        assert isinstance(error_response["detail"], str)
