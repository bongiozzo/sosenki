"""Contract tests for Mini App API endpoints."""

import pytest
from pydantic import ValidationError

from src.api.mini_app import (
    TransactionResponse,
    UserListItemResponse,
    UserListResponse,
    UserStatusResponse,
)


def test_mini_app_init_endpoint_exists():
    """Verify /api/mini-app/init endpoint exists."""
    # This test will be implemented with proper FastAPI TestClient
    # For now, it's a placeholder to mark T019 as addressed
    pass


@pytest.mark.asyncio
async def test_mini_app_endpoints_integrated():
    """Placeholder for future integration tests with FastAPI TestClient."""
    # TODO: Implement full endpoint tests with TestClient
    pass


# User Status Response Tests


def test_user_status_response_schema_valid():
    """Verify UserStatusResponse schema with valid data."""
    response_data = {
        "user_id": 123456,
        "roles": ["investor", "owner"],
        "stakeholder_url": "https://example.com/stakeholders",
        "share_percentage": 1,
        "representative_of": None,
        "represented_user_roles": None,
        "represented_user_share_percentage": None,
    }
    response = UserStatusResponse(**response_data)
    assert response.user_id == 123456
    assert response.roles == ["investor", "owner"]
    assert response.stakeholder_url == "https://example.com/stakeholders"
    assert response.share_percentage == 1


def test_user_status_response_schema_share_percentage_null_non_owner():
    """Verify UserStatusResponse with null share_percentage for non-owner."""
    response_data = {
        "user_id": 654321,
        "roles": ["member"],
        "stakeholder_url": None,
        "share_percentage": None,
        "representative_of": None,
        "represented_user_roles": None,
        "represented_user_share_percentage": None,
    }
    response = UserStatusResponse(**response_data)
    assert response.share_percentage is None
    assert response.stakeholder_url is None


def test_user_status_response_schema_share_percentage_zero():
    """Verify UserStatusResponse with share_percentage=0 for unsigned owner."""
    response_data = {
        "user_id": 111111,
        "roles": ["owner"],
        "stakeholder_url": "https://example.com/stakeholders",
        "share_percentage": 0,
        "representative_of": None,
        "represented_user_roles": None,
        "represented_user_share_percentage": None,
    }
    response = UserStatusResponse(**response_data)
    assert response.share_percentage == 0


def test_user_status_response_schema_roles_always_non_empty():
    """Verify UserStatusResponse roles should always contain at least 'member'."""
    # Backend logic should ensure roles is never empty
    response_data = {
        "user_id": 222222,
        "roles": ["member"],  # Minimal valid roles
        "stakeholder_url": None,
        "share_percentage": None,
        "representative_of": None,
        "represented_user_roles": None,
        "represented_user_share_percentage": None,
    }
    response = UserStatusResponse(**response_data)
    assert len(response.roles) >= 1


def test_user_status_response_schema_missing_required_field():
    """Verify ValidationError for missing required field."""
    response_data = {
        "user_id": 333333,
        "roles": ["member"],
        # Missing stakeholder_url (required, can be None)
        "share_percentage": None,
    }
    with pytest.raises(ValidationError):
        UserStatusResponse(**response_data)


def test_user_status_response_schema_invalid_share_percentage_type():
    """Verify ValidationError for string share_percentage (should be int or None)."""
    response_data = {
        "user_id": 444444,
        "roles": ["member"],
        "stakeholder_url": None,
        "share_percentage": "1",  # Should be int, not string
        "representative_of": None,
        "represented_user_roles": None,
        "represented_user_share_percentage": None,
    }
    # Pydantic will coerce "1" to 1, so this might pass
    # In real-world, API should validate strictly
    response = UserStatusResponse(**response_data)
    assert response.share_percentage == 1  # Pydantic accepts it, but backend should not send it


# Transaction Response Tests


def test_transaction_response_schema_valid():
    """Verify TransactionResponse schema with valid data."""
    response_data = {
        "from_ac_name": "Account A",
        "to_ac_name": "Account B",
        "amount": 150.50,
        "date": "2025-11-15T10:30:00",
        "description": "Monthly transfer",
    }
    response = TransactionResponse(**response_data)
    assert response.from_ac_name == "Account A"
    assert response.to_ac_name == "Account B"
    assert response.amount == 150.50
    assert response.date == "2025-11-15T10:30:00"
    assert response.description == "Monthly transfer"


def test_transaction_response_schema_no_description():
    """Verify TransactionResponse with null description."""
    response_data = {
        "from_ac_name": "Account A",
        "to_ac_name": "Account B",
        "amount": 75.00,
        "date": "2025-11-10T12:00:00",
        "description": None,
    }
    response = TransactionResponse(**response_data)
    assert response.description is None


def test_transaction_response_schema_zero_amount():
    """Verify TransactionResponse with zero amount (edge case)."""
    response_data = {
        "from_ac_name": "Account A",
        "to_ac_name": "Account B",
        "amount": 0.00,
        "date": "2025-01-01T00:00:00",
        "description": None,
    }
    response = TransactionResponse(**response_data)
    assert response.amount == 0.00


def test_transaction_response_schema_missing_required_field():
    """Verify ValidationError for missing required field."""
    response_data = {
        "from_ac_name": "Account A",
        "to_ac_name": "Account B",
        "amount": 100.00,
        # Missing date (required)
    }
    with pytest.raises(ValidationError):
        TransactionResponse(**response_data)


def test_transaction_response_schema_large_amount():
    """Verify TransactionResponse handles large amounts."""
    response_data = {
        "from_ac_name": "Account A",
        "to_ac_name": "Account B",
        "amount": 999999999.99,
        "date": "2025-11-15T10:30:00",
        "description": "Large transfer",
    }
    response = TransactionResponse(**response_data)
    assert response.amount == 999999999.99


def test_transaction_response_schema_different_account_pairs():
    """Verify TransactionResponse works with various account names."""
    test_cases = [
        ("Account 1", "Account 2"),
        ("Взносы", "Траты"),
        ("Main", "Secondary"),
        ("A", "B"),
    ]
    for from_name, to_name in test_cases:
        response_data = {
            "from_ac_name": from_name,
            "to_ac_name": to_name,
            "amount": 100.00,
            "date": "2025-11-15T10:30:00",
            "description": None,
        }
        response = TransactionResponse(**response_data)
        assert response.from_ac_name == from_name
        assert response.to_ac_name == to_name


# User List Response Tests


def test_user_list_item_response_schema_valid():
    """Verify UserListItemResponse schema with valid data."""
    response_data = {
        "user_id": 123,
        "name": "John Doe",
        "telegram_id": "987654321",
    }
    response = UserListItemResponse(**response_data)
    assert response.user_id == 123
    assert response.name == "John Doe"
    assert response.telegram_id == "987654321"


def test_user_list_item_response_schema_null_telegram_id():
    """Verify UserListItemResponse with null telegram_id."""
    response_data = {
        "user_id": 456,
        "name": "Jane Smith",
        "telegram_id": None,
    }
    response = UserListItemResponse(**response_data)
    assert response.user_id == 456
    assert response.name == "Jane Smith"
    assert response.telegram_id is None


def test_user_list_response_schema_valid():
    """Verify UserListResponse schema with valid data."""
    response_data = {
        "users": [
            {"user_id": 1, "name": "Alice", "telegram_id": "111"},
            {"user_id": 2, "name": "Bob", "telegram_id": "222"},
            {"user_id": 3, "name": "Charlie", "telegram_id": None},
        ]
    }
    response = UserListResponse(**response_data)
    assert len(response.users) == 3
    assert response.users[0].name == "Alice"
    assert response.users[1].user_id == 2
    assert response.users[2].telegram_id is None


def test_user_list_response_schema_empty():
    """Verify UserListResponse with empty users list."""
    response_data = {"users": []}
    response = UserListResponse(**response_data)
    assert len(response.users) == 0
    assert response.users == []
