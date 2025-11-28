"""Unit tests for auth_service helper functions with focused coverage."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.user import User
from src.services.auth_service import _extract_init_data, resolve_target_user


class TestExtractInitData:
    """Test cases for _extract_init_data helper."""

    def test_extract_from_authorization_header(self):
        """Test extraction from Authorization header."""
        result = _extract_init_data("tma raw_data_here", None, None)
        assert result == "raw_data_here"

    def test_extract_from_authorization_header_case_insensitive(self):
        """Test extraction from Authorization header is case-insensitive."""
        result = _extract_init_data("TMA raw_data_here", None, None)
        assert result == "raw_data_here"

    def test_extract_from_custom_header(self):
        """Test extraction from X-Telegram-Init-Data header."""
        result = _extract_init_data(None, "header_raw_data", None)
        assert result == "header_raw_data"

    def test_extract_from_body_initDataRaw(self):
        """Test extraction from body initDataRaw field."""
        result = _extract_init_data(None, None, {"initDataRaw": "body_raw_data"})
        assert result == "body_raw_data"

    def test_extract_from_body_initData(self):
        """Test extraction from body initData field."""
        result = _extract_init_data(None, None, {"initData": "body_init_data"})
        assert result == "body_init_data"

    def test_extract_from_body_init_data_raw(self):
        """Test extraction from body init_data_raw field."""
        result = _extract_init_data(None, None, {"init_data_raw": "body_snake_raw"})
        assert result == "body_snake_raw"

    def test_extract_from_body_init_data(self):
        """Test extraction from body init_data field."""
        result = _extract_init_data(None, None, {"init_data": "body_snake_init"})
        assert result == "body_snake_init"

    def test_extract_priority_authorization_over_header(self):
        """Test Authorization header has priority over X-Telegram-Init-Data."""
        result = _extract_init_data("tma auth_data", "header_data", None)
        assert result == "auth_data"

    def test_extract_priority_header_over_body(self):
        """Test X-Telegram-Init-Data header has priority over body."""
        result = _extract_init_data(None, "header_data", {"initDataRaw": "body_data"})
        assert result == "header_data"

    def test_extract_ignores_empty_body_fields(self):
        """Test empty body fields are skipped."""
        result = _extract_init_data(None, None, {"initDataRaw": "", "initData": "valid_data"})
        assert result == "valid_data"

    def test_extract_none_when_all_missing(self):
        """Test returns None when no init data found."""
        result = _extract_init_data(None, None, None)
        assert result is None

    def test_extract_none_when_body_invalid_type(self):
        """Test returns None when body is not a dict."""
        result = _extract_init_data(None, None, "not_a_dict")
        assert result is None


class TestResolveTargetUser:
    """Test cases for resolve_target_user helper - using mocking to avoid DB calls."""

    @pytest.mark.asyncio
    async def test_resolve_active_user_no_representation(self):
        """Test resolving active user without representation."""
        mock_session = AsyncMock()
        mock_user = User(id=1, telegram_id="123", is_active=True, is_administrator=False)

        with patch("src.services.auth_service.UserService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_by_telegram_id = AsyncMock(return_value=mock_user)
            mock_service_class.return_value = mock_service

            target, switched = await resolve_target_user(mock_session, mock_user)
            assert target == mock_user
            assert switched is False
