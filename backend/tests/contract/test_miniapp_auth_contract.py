"""
Contract tests for POST /miniapp/auth endpoint.

These tests verify that the API endpoint matches the OpenAPI contract
defined in specs/001-seamless-telegram-auth/contracts/openapi.yaml

Test-First: These tests are written before implementation and should FAIL initially.
They will PASS once the implementation is complete.
"""

import pytest
import json
import hmac
import hashlib
import time
import urllib.parse
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.user import SOSenkiUser


@pytest.fixture(scope="function")
def test_client(test_db_session):
    """Provide a FastAPI test client with test database session."""
    return TestClient(app)


@pytest.fixture
def valid_initdata_string() -> tuple:
    """Create a valid URL-encoded initData string with correct HMAC hash."""
    bot_token = "test_bot_token"
    user_id = 123456789
    auth_date = int(time.time())

    # Build user object
    user_obj = {
        "id": user_id,
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "language_code": "en",
        "is_premium": False,
    }

    # Create check string (all fields except hash, sorted alphabetically)
    user_json = json.dumps(user_obj)
    user_encoded = urllib.parse.quote(user_json)

    check_parts = [
        f"auth_date={auth_date}",
        f"user={user_encoded}",
    ]
    check_string = "\n".join(sorted(check_parts))

    # Compute secret key: HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()

    # Compute hash: HMAC-SHA256(check_string, secret_key)
    data_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    # Build full initData string
    initdata_parts = [
        f"auth_date={auth_date}",
        f"hash={data_hash}",
        f"user={user_encoded}",
    ]
    initdata_string = "&".join(sorted(initdata_parts))

    return initdata_string, user_id, auth_date


class TestMiniAppAuthContract:
    """Contract tests for the Mini App auth endpoint."""

    def test_miniapp_auth_endpoint_exists(
        self, test_client: TestClient, valid_initdata_string: tuple
    ) -> None:
        """
        Test: POST /miniapp/auth endpoint is callable and returns 200 or 401.

        Expected behavior (from spec):
        - Endpoint: POST /miniapp/auth
        - Request: { "init_data": "..." }
        - Response 200: { "linked": bool, "user": User?, "request_form": Object? }
        - Response 401: Invalid or expired initData
        """
        initdata_string, user_id, auth_date = valid_initdata_string

        # POST to /miniapp/auth with valid initData
        payload = {"init_data": initdata_string}
        response = test_client.post("/miniapp/auth", json=payload)

        # Assert response status is 200 (linked or unlinked)
        assert response.status_code in (
            200,
            401,
        ), f"Unexpected status: {response.status_code}, body: {response.text}"

    def test_miniapp_auth_linked_user_response_schema(
        self, test_client: TestClient, test_db_session, valid_initdata_string: tuple
    ) -> None:
        """
        Test: When Telegram ID is linked, response includes linked=true and user object.

        Expected response shape (from OpenAPI schema):
        {
            "linked": true,
            "user": {
                "id": "uuid",
                "telegram_id": 123456789,
                "email": "user@example.com",
                "roles": ["User", "Administrator", ...]
            },
            "request_form": null
        }
        """
        initdata_string, user_id, auth_date = valid_initdata_string

        # Create a linked user in database
        linked_user = SOSenkiUser(
            telegram_id=user_id,
            email="linked@example.com",
            first_name="Test",
            last_name="User",
            roles=["User"],
        )
        test_db_session.add(linked_user)
        test_db_session.commit()

        # POST to /miniapp/auth
        payload = {"init_data": initdata_string}
        response = test_client.post("/miniapp/auth", json=payload)

        # Assert 200 OK
        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"

        # Assert response schema
        data = response.json()
        assert data["linked"] is True
        assert data["user"] is not None
        assert data["user"]["telegram_id"] == user_id
        assert data["user"]["email"] == "linked@example.com"
        assert data["request_form"] is None

    def test_miniapp_auth_unlinked_user_response_schema(
        self, test_client: TestClient, test_db_session, valid_initdata_string: tuple
    ) -> None:
        """
        Test: When Telegram ID is not linked, response includes linked=false and request_form.

        Expected response shape (from OpenAPI schema):
        {
            "linked": false,
            "user": null,
            "request_form": {
                "telegram_id": 123456789,
                "first_name": "Test",
                "note": "Optional message"
            }
        }
        """
        initdata_string, user_id, auth_date = valid_initdata_string

        # Ensure no linked user exists
        existing = test_db_session.query(SOSenkiUser).filter_by(telegram_id=user_id).first()
        assert existing is None, "User should not exist for this test"

        # POST to /miniapp/auth
        payload = {"init_data": initdata_string}
        response = test_client.post("/miniapp/auth", json=payload)

        # Assert 200 OK
        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"

        # Assert response schema
        data = response.json()
        assert data["linked"] is False
        assert data["user"] is None
        assert data["request_form"] is not None
        assert data["request_form"]["telegram_id"] == user_id
        assert data["request_form"]["first_name"] == "Test"

    def test_miniapp_auth_invalid_initdata_returns_401(self, test_client: TestClient) -> None:
        """
        Test: Invalid or expired initData results in 401 Unauthorized.

        Invalid scenarios:
        - Missing or tampered hash
        - Expired auth_date (> INITDATA_EXPIRATION_SECONDS, default 120s)
        - Malformed payload
        """
        # Test 1: Invalid hash
        invalid_initdata_1 = "auth_date=1730629500&hash=invalid&user=%7B%22id%22%3A123456789%7D"
        payload = {"init_data": invalid_initdata_1}
        response = test_client.post("/miniapp/auth", json=payload)
        assert (
            response.status_code == 401
        ), f"Expected 401 for invalid hash, got {response.status_code}"

        # Test 2: Missing hash
        invalid_initdata_2 = "auth_date=1730629500&user=%7B%22id%22%3A123456789%7D"
        payload = {"init_data": invalid_initdata_2}
        response = test_client.post("/miniapp/auth", json=payload)
        assert (
            response.status_code == 401
        ), f"Expected 401 for missing hash, got {response.status_code}"

        # Test 3: Expired auth_date (5 minutes ago)
        old_auth_date = int(time.time()) - 300
        bot_token = "test_bot_token"
        user_id = 999999999  # Different user to avoid interference
        user_obj = {"id": user_id, "first_name": "Old", "last_name": "User"}
        user_json = json.dumps(user_obj)
        user_encoded = urllib.parse.quote(user_json)

        check_parts = [
            f"auth_date={old_auth_date}",
            f"user={user_encoded}",
        ]
        check_string = "\n".join(sorted(check_parts))
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        data_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

        expired_initdata = f"auth_date={old_auth_date}&hash={data_hash}&user={user_encoded}"
        payload = {"init_data": expired_initdata}
        response = test_client.post("/miniapp/auth", json=payload)
        assert (
            response.status_code == 401
        ), f"Expected 401 for expired auth_date, got {response.status_code}"
