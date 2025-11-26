"""Unit tests for mini app helper functions and utilities."""


class TestExtractInitData:
    """Test _extract_init_data function with various input combinations."""

    def test_extract_from_authorization_header(self):
        """Verify _extract_init_data extracts from Authorization header."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data("tma test_value", None, None)
        assert result == "test_value"

    def test_extract_from_authorization_case_insensitive(self):
        """Verify _extract_init_data handles TMA case-insensitively."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data("TMA test_value", None, None)
        assert result == "test_value"

    def test_extract_from_authorization_tMa_mixed_case(self):
        """Verify _extract_init_data handles tMa case."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data("tMa test_value", None, None)
        assert result == "test_value"

    def test_extract_from_x_telegram_header(self):
        """Verify _extract_init_data extracts from X-Telegram-Init-Data header."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data(None, "header_value", None)
        assert result == "header_value"

    def test_extract_from_body_init_data_raw(self):
        """Verify _extract_init_data extracts initDataRaw from body."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data(None, None, {"initDataRaw": "body_value"})
        assert result == "body_value"

    def test_extract_from_body_init_data(self):
        """Verify _extract_init_data extracts initData from body."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data(None, None, {"initData": "body_value"})
        assert result == "body_value"

    def test_extract_from_body_init_data_raw_underscore(self):
        """Verify _extract_init_data extracts init_data_raw from body."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data(None, None, {"init_data_raw": "body_value"})
        assert result == "body_value"

    def test_extract_from_body_init_data_underscore(self):
        """Verify _extract_init_data extracts init_data from body."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data(None, None, {"init_data": "body_value"})
        assert result == "body_value"

    def test_extract_returns_none_when_empty(self):
        """Verify _extract_init_data returns None when no data provided."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data(None, None, None)
        assert result is None

    def test_extract_skips_whitespace_only(self):
        """Verify _extract_init_data skips whitespace-only values."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data(None, None, {"initData": "   "})
        assert result is None

    def test_extract_skips_non_string_body_values(self):
        """Verify _extract_init_data skips non-string body values."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data(None, None, {"initData": 123})
        assert result is None

    def test_extract_skips_non_dict_body(self):
        """Verify _extract_init_data skips non-dict body values."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data(None, None, "not_a_dict")
        assert result is None

    def test_extract_priority_authorization_over_header(self):
        """Verify _extract_init_data prioritizes Authorization over header."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data("tma auth_value", "header_value", None)
        assert result == "auth_value"

    def test_extract_priority_header_over_body(self):
        """Verify _extract_init_data prioritizes header over body."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data(None, "header_value", {"initData": "body_value"})
        assert result == "header_value"

    def test_extract_authorization_empty_string(self):
        """Verify _extract_init_data returns None for empty authorization."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data("", None, None)
        assert result is None

    def test_extract_authorization_whitespace_only(self):
        """Verify _extract_init_data returns None for whitespace-only authorization."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data("   ", None, None)
        assert result is None

    def test_extract_authorization_without_tma_prefix(self):
        """Verify _extract_init_data returns None for auth without tma prefix."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data("Bearer test_value", None, None)
        assert result is None

    def test_extract_with_extra_whitespace_in_auth(self):
        """Verify _extract_init_data strips extra whitespace."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data("  tma   test_value  ", None, None)
        assert result == "test_value"

    def test_extract_with_empty_body_dict(self):
        """Verify _extract_init_data handles empty body dict."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data(None, None, {})
        assert result is None

    def test_extract_body_priority_initDataRaw_first(self):
        """Verify _extract_init_data checks initDataRaw before other keys."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data(
            None, None, {"initDataRaw": "raw_value", "initData": "data_value"}
        )
        assert result == "raw_value"


class TestResponseSchemas:
    """Test response schema classes."""

    def test_user_status_response_schema_minimal(self):
        """Verify UserStatusResponse with minimal required fields."""
        from src.api.mini_app import UserStatusResponse

        response_data = {
            "user_id": 123456,
            "account_id": 1,
            "roles": ["member"],
            "stakeholder_url": None,
            "share_percentage": None,
            "representative_of": None,
            "represented_user_roles": None,
            "represented_user_share_percentage": None,
        }
        response = UserStatusResponse(**response_data)
        assert response.user_id == 123456
        assert response.account_id == 1
        assert response.roles == ["member"]

    def test_user_list_response_schema_multiple_users(self):
        """Verify UserListResponse with multiple users."""
        from src.api.mini_app import UserListItemResponse, UserListResponse

        user1 = UserListItemResponse(user_id=1, name="Alice", telegram_id="111")
        user2 = UserListItemResponse(user_id=2, name="Bob", telegram_id="222")
        response = UserListResponse(users=[user1, user2])
        assert len(response.users) == 2
        assert response.users[0].name == "Alice"

    def test_transaction_response_schema_full_fields(self):
        """Verify TransactionResponse with all fields."""
        from src.api.mini_app import TransactionResponse

        response_data = {
            "from_account_id": 1,
            "from_ac_name": "Account A",
            "to_account_id": 2,
            "to_ac_name": "Account B",
            "amount": 150.50,
            "date": "2025-11-15T10:30:00",
            "description": "Monthly transfer",
        }
        response = TransactionResponse(**response_data)
        assert response.from_account_id == 1
        assert response.to_account_id == 2
        assert response.amount == 150.50
        assert response.description == "Monthly transfer"

    def test_property_response_schema_valid(self):
        """Verify PropertyResponse with valid data."""
        from src.api.mini_app import PropertyResponse

        response_data = {
            "id": 42,
            "property_name": "Main Property",
            "type": "apartment",
            "share_weight": "100",
            "is_ready": True,
            "is_for_tenant": False,
            "photo_link": "https://example.com/photo.jpg",
            "sale_price": "500000",
            "main_property_id": None,
        }
        response = PropertyResponse(**response_data)
        assert response.id == 42
        assert response.property_name == "Main Property"


class TestTelegramSignatureVerification:
    """Test Telegram signature verification."""

    def test_verify_telegram_signature_invalid_data(self):
        """Verify verify_telegram_webapp_signature with invalid data."""
        from src.services.user_service import UserService

        result = UserService.verify_telegram_webapp_signature("", "test_token")
        assert result is None

    def test_verify_telegram_signature_wrong_signature(self):
        """Verify verify_telegram_webapp_signature rejects wrong signature."""
        from src.services.user_service import UserService

        # This init data format is wrong, should not verify
        init_data = "query_id=123&user={"
        result = UserService.verify_telegram_webapp_signature(init_data, "test_token")
        assert result is None
