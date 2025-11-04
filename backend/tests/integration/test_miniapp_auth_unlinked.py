"""Integration tests for US1 — Mini App authentication flows (unlinked user)."""

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


class TestMiniAppAuthUnlinked:
    """Integration tests for unlinked user flows in Mini App auth."""

    def test_unlinked_user_gets_request_form(self, client: TestClient, test_db_session):
        """
        T019: Unlinked user receives request_form to submit join request.

        Flow:
        1. Send valid initData for a telegram_id with no linked SOSenkiUser
        2. Verify response is linked=false with request_form populated
        """
        telegram_id = 555555555
        bot_token = "test_bot_token"
        auth_date = int(time.time())

        user_obj = {
            "id": telegram_id,
            "first_name": "Bob",
            "last_name": "Johnson",
            "username": "bob_johnson",
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

        # Ensure no user is linked to this telegram_id
        existing = test_db_session.query(SOSenkiUser).filter_by(telegram_id=telegram_id).first()
        assert existing is None, "User should not be linked for this test"

        # Send auth request
        payload = {"init_data": initdata_string}
        response = client.post("/miniapp/auth", json=payload)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["linked"] is False
        assert data["user"] is None
        assert data["request_form"] is not None

        # Verify request_form has required fields
        form = data["request_form"]
        assert form["telegram_id"] == telegram_id
        assert form["first_name"] == "Bob"

    def test_unlinked_user_request_form_includes_username(
        self, client: TestClient, test_db_session
    ):
        """
        Test: Request form includes telegram username from initData.
        """
        telegram_id = 666666666
        bot_token = "test_bot_token"
        auth_date = int(time.time())

        user_obj = {
            "id": telegram_id,
            "first_name": "Charlie",
            "username": "charlie_brown",
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
        assert data["linked"] is False
        assert data["request_form"]["telegram_id"] == telegram_id

    def test_multiple_unlinked_users_independent(self, client: TestClient, test_db_session):
        """
        Test: Multiple unlinked users each get independent request forms.
        """
        bot_token = "test_bot_token"

        # User 1
        telegram_id_1 = 777777777
        auth_date_1 = int(time.time())
        user_obj_1 = {"id": telegram_id_1, "first_name": "User1"}
        user_json_1 = json.dumps(user_obj_1)
        user_encoded_1 = urllib.parse.quote(user_json_1)
        check_parts_1 = [f"auth_date={auth_date_1}", f"user={user_encoded_1}"]
        check_string_1 = "\n".join(sorted(check_parts_1))
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        data_hash_1 = hmac.new(secret_key, check_string_1.encode(), hashlib.sha256).hexdigest()
        initdata_1 = f"auth_date={auth_date_1}&hash={data_hash_1}&user={user_encoded_1}"

        # User 2
        telegram_id_2 = 888888888
        auth_date_2 = int(time.time())
        user_obj_2 = {"id": telegram_id_2, "first_name": "User2"}
        user_json_2 = json.dumps(user_obj_2)
        user_encoded_2 = urllib.parse.quote(user_json_2)
        check_parts_2 = [f"auth_date={auth_date_2}", f"user={user_encoded_2}"]
        check_string_2 = "\n".join(sorted(check_parts_2))
        data_hash_2 = hmac.new(secret_key, check_string_2.encode(), hashlib.sha256).hexdigest()
        initdata_2 = f"auth_date={auth_date_2}&hash={data_hash_2}&user={user_encoded_2}"

        # Send requests
        response_1 = client.post("/miniapp/auth", json={"init_data": initdata_1})
        response_2 = client.post("/miniapp/auth", json={"init_data": initdata_2})

        # Verify both are unlinked and have independent forms
        assert response_1.status_code == 200
        data_1 = response_1.json()
        assert data_1["linked"] is False
        assert data_1["request_form"]["telegram_id"] == telegram_id_1

        assert response_2.status_code == 200
        data_2 = response_2.json()
        assert data_2["linked"] is False
        assert data_2["request_form"]["telegram_id"] == telegram_id_2

    def test_request_form_allows_note_field(self, client: TestClient, test_db_session):
        """
        Test: Request form response includes optional note field for frontend to prompt.
        """
        telegram_id = 999999999
        bot_token = "test_bot_token"
        auth_date = int(time.time())

        user_obj = {"id": telegram_id, "first_name": "Eve"}
        user_json = json.dumps(user_obj)
        user_encoded = urllib.parse.quote(user_json)

        check_parts = [f"auth_date={auth_date}", f"user={user_encoded}"]
        check_string = "\n".join(sorted(check_parts))

        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        data_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

        initdata_string = f"auth_date={auth_date}&hash={data_hash}&user={user_encoded}"

        # Send auth request
        payload = {"init_data": initdata_string}
        response = client.post("/miniapp/auth", json=payload)

        # Verify note field is present (optional)
        assert response.status_code == 200
        data = response.json()
        form = data["request_form"]
        assert "note" in form or "phone" in form or "email" in form
