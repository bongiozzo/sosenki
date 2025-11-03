"""Integration tests for US1 — Mini App authentication flows (happy path)."""

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
def client(test_db_session):
    """Provide a FastAPI test client with test database."""
    return TestClient(app)


@pytest.fixture
def valid_initdata_linked_user() -> tuple:
    """Create valid initData for an existing linked user."""
    bot_token = "test_bot_token"
    user_id = 111111111
    auth_date = int(time.time())

    user_obj = {
        "id": user_id,
        "first_name": "Alice",
        "last_name": "Smith",
        "username": "alice_smith",
    }

    user_json = json.dumps(user_obj)
    user_encoded = urllib.parse.quote(user_json)

    check_parts = [
        f"auth_date={auth_date}",
        f"user={user_encoded}",
    ]
    check_string = "\n".join(sorted(check_parts))

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()

    data_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    initdata_parts = [
        f"auth_date={auth_date}",
        f"hash={data_hash}",
        f"user={user_encoded}",
    ]
    initdata_string = "&".join(sorted(initdata_parts))

    return initdata_string, user_id


class TestMiniAppAuthIntegration:
    """Integration tests for Mini App auth endpoint."""

    def test_linked_user_sees_welcome(self, client: TestClient, test_db_session):
        """
        T018: Linked user gets welcome response with user data.

        Flow:
        1. Create a SOSenkiUser with a telegram_id
        2. Send valid initData with that telegram_id
        3. Verify response is linked=true with user object
        """
        # Create a linked user
        telegram_id = 222222222
        linked_user = SOSenkiUser(
            telegram_id=telegram_id,
            email="alice@example.com",
            first_name="Alice",
            last_name="Smith",
            roles=["User"],
        )
        test_db_session.add(linked_user)
        test_db_session.commit()

        # Create valid initData for this user
        bot_token = "test_bot_token"
        auth_date = int(time.time())

        user_obj = {
            "id": telegram_id,
            "first_name": "Alice",
            "last_name": "Smith",
            "username": "alice_smith",
        }

        user_json = json.dumps(user_obj)
        user_encoded = urllib.parse.quote(user_json)

        check_parts = [
            f"auth_date={auth_date}",
            f"user={user_encoded}",
        ]
        check_string = "\n".join(sorted(check_parts))

        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()

        data_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

        initdata_parts = [
            f"auth_date={auth_date}",
            f"hash={data_hash}",
            f"user={user_encoded}",
        ]
        initdata_string = "&".join(sorted(initdata_parts))

        # Send auth request
        payload = {"init_data": initdata_string}
        response = client.post("/miniapp/auth", json=payload)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["linked"] is True
        assert data["user"] is not None
        assert data["user"]["telegram_id"] == telegram_id
        assert data["user"]["email"] == "alice@example.com"
        assert data["request_form"] is None

    def test_linked_user_multiple_roles(self, client: TestClient, test_db_session):
        """
        Test: Linked user with multiple roles sees all roles in welcome.
        """
        telegram_id = 333333333
        linked_user = SOSenkiUser(
            telegram_id=telegram_id,
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            roles=["Administrator", "User"],
        )
        test_db_session.add(linked_user)
        test_db_session.commit()

        # Create valid initData
        bot_token = "test_bot_token"
        auth_date = int(time.time())

        user_obj = {"id": telegram_id, "first_name": "Admin"}
        user_json = json.dumps(user_obj)
        user_encoded = urllib.parse.quote(user_json)

        check_parts = [
            f"auth_date={auth_date}",
            f"user={user_encoded}",
        ]
        check_string = "\n".join(sorted(check_parts))

        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        data_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

        initdata_parts = [
            f"auth_date={auth_date}",
            f"hash={data_hash}",
            f"user={user_encoded}",
        ]
        initdata_string = "&".join(sorted(initdata_parts))

        # Send auth request
        payload = {"init_data": initdata_string}
        response = client.post("/miniapp/auth", json=payload)

        # Verify response includes all roles
        assert response.status_code == 200
        data = response.json()
        assert data["linked"] is True
        assert "Administrator" in data["user"]["roles"]
        assert "User" in data["user"]["roles"]

    def test_response_contains_required_fields(self, client: TestClient, test_db_session):
        """
        Test: Response for linked user contains all required fields per OpenAPI spec.
        """
        telegram_id = 444444444
        linked_user = SOSenkiUser(
            telegram_id=telegram_id,
            email="user@example.com",
            first_name="John",
            last_name="Doe",
            roles=["User"],
        )
        test_db_session.add(linked_user)
        test_db_session.commit()

        # Create valid initData
        bot_token = "test_bot_token"
        auth_date = int(time.time())
        user_obj = {"id": telegram_id, "first_name": "John"}
        user_json = json.dumps(user_obj)
        user_encoded = urllib.parse.quote(user_json)

        check_parts = [
            f"auth_date={auth_date}",
            f"user={user_encoded}",
        ]
        check_string = "\n".join(sorted(check_parts))

        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        data_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

        initdata_parts = [
            f"auth_date={auth_date}",
            f"hash={data_hash}",
            f"user={user_encoded}",
        ]
        initdata_string = "&".join(sorted(initdata_parts))

        # Send auth request
        payload = {"init_data": initdata_string}
        response = client.post("/miniapp/auth", json=payload)

        # Verify all required fields are present
        assert response.status_code == 200
        data = response.json()

        # Top-level fields
        assert "linked" in data
        assert "user" in data
        assert "request_form" in data

        # User object fields (when linked)
        if data["linked"]:
            user = data["user"]
            assert "id" in user
            assert "telegram_id" in user
            assert "email" in user
            assert "roles" in user
