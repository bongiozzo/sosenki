"""Comprehensive tests for Mini App endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.mini_app import (
    TransactionResponse,
    UserContextResponse,
    UserListItemResponse,
)
from src.main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


class TestInitEndpoint:
    """Tests for /api/mini-app/init endpoint."""

    def test_signature_verification_exception_returns_500(self, client: TestClient):
        """Test server error handling when signature verification raises exception."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature",
            side_effect=Exception("Database error"),
        ):
            response = client.post(
                "/api/mini-app/init",
                headers={"Authorization": "tma test"},
            )
            assert response.status_code == 500


# ============================================================================
# Response Schema Tests - These test Pydantic model validation
# ============================================================================


class TestUserContextResponseSchema:
    """Tests for UserContextResponse Pydantic model."""

    def test_user_context_response_valid_full_data(self):
        """Verify UserContextResponse schema with complete valid data."""
        response_data = {
            "user_id": 123456,
            "name": "Test User",
            "account_id": 1,
            "roles": ["investor", "owner", "stakeholder"],
        }
        response = UserContextResponse(**response_data)
        assert response.user_id == 123456
        assert response.account_id == 1
        assert response.roles == ["investor", "owner", "stakeholder"]

    def test_user_context_response_investor_only(self):
        """Verify UserContextResponse with investor-only role."""
        response_data = {
            "user_id": 789,
            "name": "Investor User",
            "account_id": 2,
            "roles": ["investor"],
        }
        response = UserContextResponse(**response_data)
        assert response.user_id == 789
        assert response.account_id == 2
        assert response.roles == ["investor"]

    def test_user_context_response_owner_role(self):
        """Verify UserContextResponse with owner and stakeholder roles."""
        response_data = {
            "user_id": 456,
            "name": "Owner User",
            "account_id": 3,
            "roles": ["owner", "stakeholder"],
        }
        response = UserContextResponse(**response_data)
        assert response.account_id == 3
        assert "owner" in response.roles
        assert "stakeholder" in response.roles


class TestUserListItemResponseSchema:
    """Tests for UserListItemResponse model."""

    def test_user_list_item_response_with_users(self):
        """Verify UserListItemResponse with multiple items."""
        item1 = UserListItemResponse(user_id=1, name="User 1")
        item2 = UserListItemResponse(user_id=2, name="User 2")
        assert item1.name == "User 1"
        assert item2.user_id == 2

    def test_user_list_item_response_properties(self):
        """Verify UserListItemResponse individual properties."""
        item = UserListItemResponse(user_id=99, name="Test User")
        assert item.user_id == 99
        assert item.name == "Test User"


class TestTransactionResponseSchema:
    """Tests for TransactionResponse model."""

    def test_transaction_response_with_description(self):
        """Verify TransactionResponse schema with description."""
        response_data = {
            "from_account_id": 1,
            "from_ac_name": "Checking",
            "to_account_id": 2,
            "to_ac_name": "Savings",
            "amount": 100.50,
            "date": "2024-01-15",
            "description": "Transfer",
        }
        response = TransactionResponse(**response_data)
        assert response.from_account_id == 1
        assert response.from_ac_name == "Checking"
        assert response.to_account_id == 2
        assert response.to_ac_name == "Savings"
        assert response.amount == 100.50
        assert response.description == "Transfer"

    def test_transaction_response_without_description(self):
        """Verify TransactionResponse without optional description."""
        response_data = {
            "from_account_id": 1,
            "from_ac_name": "Checking",
            "to_account_id": 2,
            "to_ac_name": "Savings",
            "amount": 200.00,
            "date": "2024-01-16",
        }
        response = TransactionResponse(**response_data)
        assert response.description is None

    def test_transaction_response_various_amounts(self):
        """Verify TransactionResponse with various amount values."""
        test_amounts = [0.01, 1.00, 100.99, 1000000.50]
        for amount in test_amounts:
            response_data = {
                "from_account_id": 1,
                "from_ac_name": "A",
                "to_account_id": 2,
                "to_ac_name": "B",
                "amount": amount,
                "date": "2024-01-01",
            }
            response = TransactionResponse(**response_data)
            assert response.amount == amount


# ============================================================================
# Integration-style tests showing typical endpoint usage patterns
# ============================================================================


class TestResponseCodes:
    """Test response codes for various scenarios."""
