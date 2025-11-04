"""
Unit tests for Telegram initData verification and validation.

These tests focus on the cryptographic verification of Telegram Web App initData:
- Hash validation (HMAC-SHA256)
- Timestamp freshness check
- Field extraction and normalization

Test-First: These tests are written before implementation and should FAIL initially.
They will PASS once backend.app.services.telegram_auth_service is implemented.
"""

import pytest
import hmac
import hashlib
import time
import urllib.parse

from backend.app.services.telegram_auth_service import verify_initdata
from backend.app.api.errors import InvalidInitDataError


class TestInitDataValidation:
    """Unit tests for initData signature and timestamp validation."""

    def _create_valid_initdata_string(
        self, bot_token: str, user_id: int = 123456789, auth_date: int = None
    ) -> tuple:
        """Helper to create a valid URL-encoded initData string with correct HMAC hash."""
        import json

        if auth_date is None:
            auth_date = int(time.time())

        # Build data dict
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

        return initdata_string, data_hash, auth_date, user_id

    def test_verify_initdata_signature_valid(self, test_telegram_id: int) -> None:
        """
        Test: Valid initData with correct HMAC-SHA256 hash passes verification.

        Telegram Web App sends initData as URL-encoded string with a hash field.
        The hash is HMAC-SHA256 of the data string using bot token as key.

        Reference: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
        """
        bot_token = "test_bot_token"
        initdata_string, expected_hash, auth_date, user_id = self._create_valid_initdata_string(
            bot_token, test_telegram_id
        )

        # Call verify_initdata with valid payload
        result = verify_initdata(initdata_string, bot_token)

        # Assert result contains verified data
        assert result is not None
        assert result["telegram_id"] == test_telegram_id
        assert result["auth_date"] == auth_date
        assert result["user"]["id"] == test_telegram_id

    def test_verify_initdata_signature_invalid(self, test_telegram_id: int) -> None:
        """
        Test: initData with tampered hash fails verification.

        If the hash field is modified or incorrect, verify_initdata should reject it.
        """
        bot_token = "test_bot_token"
        initdata_string, correct_hash, auth_date, user_id = self._create_valid_initdata_string(
            bot_token, test_telegram_id
        )

        # Tamper with the hash
        tampered_hash = "0" * 64  # Invalid hash
        tampered_initdata = initdata_string.replace(correct_hash, tampered_hash)

        # Call verify_initdata should raise InvalidInitDataError
        with pytest.raises(InvalidInitDataError):
            verify_initdata(tampered_initdata, bot_token)

    def test_initdata_timestamp_fresh(self, test_telegram_id: int) -> None:
        """
        Test: initData with recent auth_date (within threshold) passes timestamp check.

        Telegram Web App includes auth_date (UNIX timestamp).
        We reject if auth_date is older than INITDATA_EXPIRATION_SECONDS (default 120 seconds).
        """
        bot_token = "test_bot_token"
        current_time = int(time.time())

        # Create initData with current timestamp
        initdata_string, _, _, _ = self._create_valid_initdata_string(
            bot_token, test_telegram_id, current_time
        )

        # Should pass verification (timestamp is fresh)
        result = verify_initdata(initdata_string, bot_token)
        assert result is not None
        assert result["auth_date"] == current_time

    def test_initdata_timestamp_expired(self, test_telegram_id: int) -> None:
        """
        Test: initData with old auth_date (> INITDATA_EXPIRATION_SECONDS) is rejected.

        Example: auth_date set to 5 minutes ago should fail if threshold is 120 seconds.
        """
        bot_token = "test_bot_token"
        old_time = int(time.time()) - 300  # 5 minutes ago

        # Create initData with old timestamp
        initdata_string, _, _, _ = self._create_valid_initdata_string(
            bot_token, test_telegram_id, old_time
        )

        # Should raise InvalidInitDataError due to expired timestamp
        with pytest.raises(InvalidInitDataError):
            verify_initdata(initdata_string, bot_token)

    def test_extract_telegram_id_from_valid_initdata(self, test_telegram_id: int) -> None:
        """
        Test: Telegram ID is correctly extracted from initData.

        initData contains a 'user' object with 'id' field (Telegram user ID).
        We should extract and return this as an integer.
        """
        bot_token = "test_bot_token"
        initdata_string, _, _, _ = self._create_valid_initdata_string(bot_token, test_telegram_id)

        # Verify and extract telegram_id
        result = verify_initdata(initdata_string, bot_token)

        assert result["telegram_id"] == test_telegram_id
        assert isinstance(result["telegram_id"], int)

    def test_initdata_missing_required_fields(self) -> None:
        """
        Test: initData missing required fields (user, auth_date, hash) is rejected.

        Required fields per Telegram docs:
        - user (object)
        - auth_date (integer)
        - hash (string)
        """
        bot_token = "test_bot_token"

        # Missing hash field
        invalid_initdata_1 = "auth_date=1730629500&user=%7B%22id%22%3A123456789%7D"

        # Missing auth_date field
        invalid_initdata_2 = "hash=abc123&user=%7B%22id%22%3A123456789%7D"

        # Missing user field
        invalid_initdata_3 = "auth_date=1730629500&hash=abc123"

        # All should raise InvalidInitDataError
        with pytest.raises(InvalidInitDataError):
            verify_initdata(invalid_initdata_1, bot_token)

        with pytest.raises(InvalidInitDataError):
            verify_initdata(invalid_initdata_2, bot_token)

        with pytest.raises(InvalidInitDataError):
            verify_initdata(invalid_initdata_3, bot_token)
