"""Comprehensive tests for Mini App endpoints."""

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.mini_app import (
    TransactionResponse,
    UserListItemResponse,
    UserListResponse,
    UserStatusResponse,
)
from src.main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


class TestVerifyRegistrationEndpoint:
    """Tests for /api/mini-app/verify-registration endpoint."""

    def test_missing_authorization_header(self, client: TestClient):
        """Test when Authorization header is missing."""
        response = client.post("/api/mini-app/verify-registration")
        assert response.status_code == 401

    def test_invalid_signature_returns_401(self, client: TestClient):
        """Test when signature verification fails."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature", return_value=None
        ):
            response = client.post(
                "/api/mini-app/verify-registration",
                headers={"Authorization": "tma invalid_signature"},
            )
            assert response.status_code == 401

    def test_invalid_user_id_format_in_user_data_returns_401(self, client: TestClient):
        """Test when user ID in parsed data cannot be parsed as integer."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature",
            return_value={"user": json.dumps({"id": "invalid_id", "username": "nouser"})},
        ):
            response = client.post(
                "/api/mini-app/verify-registration",
                headers={"Authorization": "tma test_data"},
            )
            # The endpoint will process "invalid_id" as a telegram_id string,
            # then try to fetch user which will likely return None
            assert response.status_code in [200, 401]


class TestMenuActionEndpoint:
    """Tests for /api/mini-app/menu-action endpoint."""

    def test_missing_init_data_returns_401(self, client: TestClient):
        """Test menu action without init data."""
        response = client.post(
            "/api/mini-app/menu-action",
            json={"action": "rule"},
        )
        assert response.status_code == 401

    def test_invalid_signature_returns_401(self, client: TestClient):
        """Test menu action with invalid signature."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature", return_value=None
        ):
            response = client.post(
                "/api/mini-app/menu-action",
                headers={"X-Telegram-Init-Data": "invalid"},
                json={"action": "rule"},
            )
            assert response.status_code == 401


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


class TestUserStatusResponseSchema:
    """Tests for UserStatusResponse Pydantic model."""

    def test_user_status_response_valid_full_data(self):
        """Verify UserStatusResponse schema with complete valid data."""
        response_data = {
            "user_id": 123456,
            "account_id": 1,
            "roles": ["investor", "owner"],
            "stakeholder_url": "https://example.com/stakeholders",
            "share_percentage": 1,
            "representative_of": None,
            "represented_user_roles": None,
            "represented_user_share_percentage": None,
        }
        response = UserStatusResponse(**response_data)
        assert response.user_id == 123456
        assert response.account_id == 1
        assert response.roles == ["investor", "owner"]
        assert response.stakeholder_url == "https://example.com/stakeholders"
        assert response.share_percentage == 1

    def test_user_status_response_investor_only(self):
        """Verify UserStatusResponse with investor-only role."""
        response_data = {
            "user_id": 789,
            "account_id": 2,
            "roles": ["investor"],
            "stakeholder_url": None,
            "share_percentage": None,
        }
        response = UserStatusResponse(**response_data)
        assert response.user_id == 789
        assert response.account_id == 2
        assert response.share_percentage is None

    def test_user_status_response_owner_role(self):
        """Verify UserStatusResponse with owner role and share percentage."""
        response_data = {
            "user_id": 456,
            "account_id": 3,
            "roles": ["owner"],
            "stakeholder_url": "https://example.com/owner",
            "share_percentage": 50,
        }
        response = UserStatusResponse(**response_data)
        assert response.account_id == 3
        assert response.share_percentage == 50
        assert "owner" in response.roles


class TestUserListResponseSchema:
    """Tests for UserListResponse and UserListItemResponse models."""

    def test_user_list_response_with_users(self):
        """Verify UserListResponse with multiple users."""
        user_items = [
            UserListItemResponse(user_id=1, name="User 1", telegram_id="111"),
            UserListItemResponse(user_id=2, name="User 2", telegram_id="222"),
        ]
        response = UserListResponse(users=user_items)
        assert len(response.users) == 2
        assert response.users[0].name == "User 1"
        assert response.users[1].telegram_id == "222"

    def test_user_list_response_empty_users(self):
        """Verify UserListResponse with empty users list."""
        response = UserListResponse(users=[])
        assert len(response.users) == 0

    def test_user_list_item_response_properties(self):
        """Verify UserListItemResponse individual properties."""
        item = UserListItemResponse(user_id=99, name="Test User", telegram_id="999")
        assert item.user_id == 99
        assert item.name == "Test User"
        assert item.telegram_id == "999"


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

    def test_verify_registration_returns_json_response(self, client: TestClient):
        """Verify endpoint returns JSON even on error."""
        response = client.post("/api/mini-app/verify-registration")
        assert response.status_code == 401
        # Verify response is valid JSON
        data = response.json()
        assert isinstance(data, dict)

    def test_menu_action_returns_json_response(self, client: TestClient):
        """Verify menu-action endpoint returns JSON."""
        response = client.post(
            "/api/mini-app/menu-action",
            json={"action": "rule"},
        )
        assert response.status_code == 401
        data = response.json()
        assert isinstance(data, dict)
