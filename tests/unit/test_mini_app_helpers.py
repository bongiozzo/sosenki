"""Unit tests for mini app helper functions and utilities."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.sql.selectable import ScalarSelect


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

    def test_user_context_response_schema_minimal(self):
        """Verify UserContextResponse with minimal required fields."""
        from src.api.mini_app import UserContextResponse

        response_data = {
            "user_id": 123456,
            "name": "Test User",
            "account_id": 1,
            "roles": ["member"],
        }
        response = UserContextResponse(**response_data)
        assert response.user_id == 123456
        assert response.account_id == 1
        assert response.roles == ["member"]

    def test_user_list_item_response_schema_multiple_users(self):
        """Verify UserListItemResponse with multiple users."""
        from src.api.mini_app import UserListItemResponse

        user1 = UserListItemResponse(user_id=1, name="Alice")
        user2 = UserListItemResponse(user_id=2, name="Bob")
        assert user1.name == "Alice"
        assert user2.user_id == 2

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


class TestInitBuildResponse:
    """Tests for _init_build_response helper."""

    @pytest.mark.asyncio
    async def test_init_build_response_admin_includes_users(self, monkeypatch):
        """Admin should see users list and stakeholder link."""
        from src.api.mini_app import InitResponse, UserContextResponse, _init_build_response

        session = AsyncMock()
        authenticated_user = SimpleNamespace(
            id=1,
            name="Admin",
            is_administrator=True,
            is_owner=False,
            representative_id=42,
        )
        target_user = SimpleNamespace(id=2, name="Target")
        user_context = UserContextResponse(user_id=2, name="Target", account_id=5, roles=["owner"])

        monkeypatch.setenv("PHOTO_GALLERY_URL", "https://photos")
        monkeypatch.setenv("STAKEHOLDER_SHARES_URL", "https://stakeholders")

        with (
            patch(
                "src.api.mini_app._build_user_context_data",
                new=AsyncMock(return_value=user_context),
            ),
            patch("src.api.mini_app.UserService") as mock_user_service,
        ):
            service_instance = MagicMock()
            service_instance.get_all_users = AsyncMock(
                return_value=[SimpleNamespace(id=99, name="Alice")]
            )
            mock_user_service.return_value = service_instance

            response = await _init_build_response(session, authenticated_user, target_user)

        assert isinstance(response, InitResponse)
        assert response.users and response.users[0].user_id == 99
        assert response.stakeholder_url == "https://stakeholders"
        assert response.photo_gallery_url == "https://photos"

    @pytest.mark.asyncio
    async def test_init_build_response_owner_without_admin(self, monkeypatch):
        """Owner (non-admin) should not load users list but gets stakeholder link."""
        from src.api.mini_app import InitResponse, UserContextResponse, _init_build_response

        session = AsyncMock()
        authenticated_user = SimpleNamespace(
            id=5,
            name="Owner",
            is_administrator=False,
            is_owner=True,
            representative_id=None,
        )
        target_user = SimpleNamespace(id=5, name="Owner")
        user_context = UserContextResponse(user_id=5, name="Owner", account_id=7, roles=["owner"])

        monkeypatch.setenv("PHOTO_GALLERY_URL", "https://photos")
        monkeypatch.setenv("STAKEHOLDER_SHARES_URL", "https://stakeholders")

        with (
            patch(
                "src.api.mini_app._build_user_context_data",
                new=AsyncMock(return_value=user_context),
            ),
            patch("src.api.mini_app.UserService") as mock_user_service,
        ):
            service_instance = MagicMock()
            service_instance.get_all_users = AsyncMock()
            mock_user_service.return_value = service_instance

            response = await _init_build_response(session, authenticated_user, target_user)

        assert isinstance(response, InitResponse)
        assert response.users is None
        assert response.stakeholder_url == "https://stakeholders"
        service_instance.get_all_users.assert_not_awaited()


class TestBuildUserContextData:
    """Tests for _build_user_context_data helper."""

    @pytest.mark.asyncio
    async def test_build_user_context_data_success(self):
        """Should return context when account exists."""
        from src.api.mini_app import UserContextResponse, _build_user_context_data

        session = AsyncMock()
        target_user = SimpleNamespace(
            id=7,
            name="Target",
            is_administrator=False,
            is_investor=False,
            is_owner=True,
            is_stakeholder=False,
            is_staff=True,
            is_tenant=False,
        )

        account = SimpleNamespace(id=55)
        result = MagicMock()
        result.scalar_one_or_none.return_value = account
        session.execute = AsyncMock(return_value=result)

        context = await _build_user_context_data(session, target_user)

        assert isinstance(context, UserContextResponse)
        assert context.account_id == 55
        assert "owner" in context.roles
        assert "staff" in context.roles

    @pytest.mark.asyncio
    async def test_build_user_context_data_missing_account(self):
        """Should raise when account is missing."""
        from src.api.mini_app import _build_user_context_data

        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result)

        target_user = SimpleNamespace(
            id=8,
            name="NoAccount",
            is_administrator=False,
            is_investor=False,
            is_owner=False,
            is_stakeholder=False,
            is_staff=False,
            is_tenant=False,
        )

        with pytest.raises(HTTPException) as exc:
            await _build_user_context_data(session, target_user)

        assert exc.value.status_code == 500


class TestBillFormattingHelpers:
    """Tests for bill helper utilities."""

    def test_format_bill_response_with_consumption(self):
        """Consumption computed when both readings present."""
        from src.api.mini_app import _format_bill_response

        bill = SimpleNamespace(
            comment="Property A",
            bill_amount=150,
            bill_type=SimpleNamespace(value="electricity"),
        )
        service_period = SimpleNamespace(
            name="2025-01",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        property_obj = SimpleNamespace(property_name="A", type="apartment")

        response = _format_bill_response(bill, service_period, property_obj, 10, 25)

        assert response["consumption"] == 15
        assert response["property_name"] == "A"
        assert response["bill_amount"] == 150

    def test_format_bill_response_without_readings(self):
        """Consumption remains None when readings missing."""
        from src.api.mini_app import _format_bill_response

        bill = SimpleNamespace(
            comment=None,
            bill_amount=200,
            bill_type=SimpleNamespace(value="shared_electricity"),
        )
        service_period = SimpleNamespace(
            name="2025-02",
            start_date=date(2025, 2, 1),
            end_date=date(2025, 2, 28),
        )

        response = _format_bill_response(bill, service_period, None, None, None)

        assert response["consumption"] is None
        assert response["property_name"] is None

    def test_build_electricity_reading_subqueries_returns_scalar(self):
        """Verify helper returns scalar select statements."""
        from src.api.mini_app import _build_electricity_reading_subqueries

        start_alias, end_alias = _build_electricity_reading_subqueries()

        assert isinstance(start_alias, ScalarSelect)
        assert isinstance(end_alias, ScalarSelect)


class TestUserContextResponseBuilder:
    """Tests for higher-level helper flows."""

    @pytest.mark.asyncio
    async def test_build_user_context_data_roles_default_member(self):
        """Ensure member role used when user has no flags."""
        from src.api.mini_app import _build_user_context_data

        session = AsyncMock()
        account = SimpleNamespace(id=77)
        result = MagicMock()
        result.scalar_one_or_none.return_value = account
        session.execute = AsyncMock(return_value=result)

        target_user = SimpleNamespace(
            id=11,
            name="Member",
            is_administrator=False,
            is_investor=False,
            is_owner=False,
            is_stakeholder=False,
            is_staff=False,
            is_tenant=False,
        )

        context = await _build_user_context_data(session, target_user)

        assert context.roles == ["member"]
