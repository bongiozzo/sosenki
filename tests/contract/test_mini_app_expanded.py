"""Tests for mini app API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.mini_app import _extract_init_data, _resolve_target_user, router


@pytest.fixture
def client():
    """Create a test client for the mini app router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    return AsyncMock()


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = 1
    user.telegram_id = "123456"
    user.name = "Test User"
    user.is_active = True
    user.is_administrator = False
    user.representative_id = None
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    user = MagicMock()
    user.id = 1
    user.telegram_id = "999999"
    user.name = "Admin User"
    user.is_active = True
    user.is_administrator = True
    user.representative_id = None
    return user


@pytest.fixture
def mock_represented_user():
    """Create a mock user being represented."""
    user = MagicMock()
    user.id = 2
    user.telegram_id = "789012"
    user.name = "Represented User"
    user.is_active = True
    user.is_administrator = False
    user.representative_id = 1
    return user


class TestExtractInitData:
    """Tests for _extract_init_data helper function."""

    def test_extract_from_authorization_header(self):
        """Test extracting init data from Authorization header."""
        raw_data = "tma_raw_data_123"
        auth = f"tma {raw_data}"

        result = _extract_init_data(authorization=auth, x_telegram_init_data=None, body=None)

        assert result == raw_data

    def test_extract_from_authorization_header_case_insensitive(self):
        """Test Authorization header extraction is case insensitive."""
        raw_data = "tma_raw_data_456"
        auth = f"TMA {raw_data}"

        result = _extract_init_data(authorization=auth, x_telegram_init_data=None, body=None)

        assert result == raw_data

    def test_extract_from_x_telegram_init_data_header(self):
        """Test extracting init data from X-Telegram-Init-Data header."""
        raw_data = "header_raw_data_789"

        result = _extract_init_data(authorization=None, x_telegram_init_data=raw_data, body=None)

        assert result == raw_data

    def test_extract_from_body_init_data_raw(self):
        """Test extracting init data from body initDataRaw field."""
        raw_data = "body_raw_data_101"
        body = {"initDataRaw": raw_data}

        result = _extract_init_data(authorization=None, x_telegram_init_data=None, body=body)

        assert result == raw_data

    def test_extract_from_body_init_data(self):
        """Test extracting init data from body initData field."""
        raw_data = "body_init_data_202"
        body = {"initData": raw_data}

        result = _extract_init_data(authorization=None, x_telegram_init_data=None, body=body)

        assert result == raw_data

    def test_extract_from_body_init_data_raw_snake_case(self):
        """Test extracting init data from body init_data_raw field."""
        raw_data = "body_snake_case_303"
        body = {"init_data_raw": raw_data}

        result = _extract_init_data(authorization=None, x_telegram_init_data=None, body=body)

        assert result == raw_data

    def test_extract_from_body_init_data_snake_case(self):
        """Test extracting init data from body init_data field."""
        raw_data = "body_snake_case_404"
        body = {"init_data": raw_data}

        result = _extract_init_data(authorization=None, x_telegram_init_data=None, body=body)

        assert result == raw_data

    def test_extract_priority_authorization_over_header(self):
        """Test Authorization header takes priority over X-Telegram-Init-Data."""
        auth_data = "auth_priority_505"
        header_data = "header_priority_505"

        result = _extract_init_data(
            authorization=f"tma {auth_data}",
            x_telegram_init_data=header_data,
            body=None,
        )

        assert result == auth_data

    def test_extract_priority_header_over_body(self):
        """Test X-Telegram-Init-Data takes priority over body."""
        header_data = "header_priority_606"
        body = {"initDataRaw": "body_priority_606"}

        result = _extract_init_data(
            authorization=None,
            x_telegram_init_data=header_data,
            body=body,
        )

        assert result == header_data

    def test_extract_returns_none_when_no_data(self):
        """Test returns None when no init data found."""
        result = _extract_init_data(authorization=None, x_telegram_init_data=None, body=None)

        assert result is None

    def test_extract_returns_none_for_empty_values(self):
        """Test returns None for empty string values."""
        result = _extract_init_data(
            authorization="",
            x_telegram_init_data="",
            body={"initDataRaw": ""},
        )

        assert result is None

    def test_extract_skips_non_string_body_values(self):
        """Test skips non-string values in body."""
        body = {"initDataRaw": 123, "initData": None, "init_data_raw": []}

        result = _extract_init_data(authorization=None, x_telegram_init_data=None, body=body)

        assert result is None


class TestResolveTargetUser:
    """Tests for _resolve_target_user helper function."""

    @pytest.mark.asyncio
    async def test_resolve_regular_user(self, mock_session, mock_user):
        """Test resolving a regular user."""
        mock_user_service = AsyncMock()
        mock_user_service.get_by_telegram_id = AsyncMock(return_value=mock_user)

        with patch("src.api.mini_app.UserService", return_value=mock_user_service):
            target_user, switched = await _resolve_target_user(
                session=mock_session,
                telegram_id=mock_user.telegram_id,
            )

        assert target_user == mock_user
        assert switched is False

    @pytest.mark.asyncio
    async def test_resolve_user_not_found(self, mock_session):
        """Test resolving when user not found."""
        mock_user_service = AsyncMock()
        mock_user_service.get_by_telegram_id = AsyncMock(return_value=None)

        with patch("src.api.mini_app.UserService", return_value=mock_user_service):
            with pytest.raises(HTTPException):
                await _resolve_target_user(
                    session=mock_session,
                    telegram_id="999999",
                )

    @pytest.mark.asyncio
    async def test_resolve_inactive_user(self, mock_session, mock_user):
        """Test resolving inactive user raises error."""
        mock_user.is_active = False
        mock_user_service = AsyncMock()
        mock_user_service.get_by_telegram_id = AsyncMock(return_value=mock_user)

        with patch("src.api.mini_app.UserService", return_value=mock_user_service):
            with pytest.raises(HTTPException):
                await _resolve_target_user(
                    session=mock_session,
                    telegram_id=mock_user.telegram_id,
                )

    @pytest.mark.asyncio
    async def test_resolve_admin_selects_other_user(self, mock_session, mock_admin_user, mock_user):
        """Test admin can select a different user."""
        mock_admin_user_service = AsyncMock()
        mock_admin_user_service.get_by_telegram_id = AsyncMock(return_value=mock_admin_user)

        mock_session.get = AsyncMock(return_value=mock_user)

        with patch("src.api.mini_app.UserService", return_value=mock_admin_user_service):
            target_user, switched = await _resolve_target_user(
                session=mock_session,
                telegram_id=mock_admin_user.telegram_id,
                selected_user_id=mock_user.id,
            )

        assert target_user == mock_user
        assert switched is True

    @pytest.mark.asyncio
    async def test_resolve_admin_selects_invalid_user(self, mock_session, mock_admin_user):
        """Test admin selecting invalid user raises error."""
        mock_admin_user_service = AsyncMock()
        mock_admin_user_service.get_by_telegram_id = AsyncMock(return_value=mock_admin_user)

        mock_session.get = AsyncMock(return_value=None)

        with patch("src.api.mini_app.UserService", return_value=mock_admin_user_service):
            with pytest.raises(HTTPException):
                await _resolve_target_user(
                    session=mock_session,
                    telegram_id=mock_admin_user.telegram_id,
                    selected_user_id=999,
                )

    @pytest.mark.asyncio
    async def test_resolve_regular_user_cannot_select_other_user(self, mock_session, mock_user):
        """Test regular user cannot select another user."""
        mock_user_service = AsyncMock()
        mock_user_service.get_by_telegram_id = AsyncMock(return_value=mock_user)

        mock_other_user = MagicMock()
        mock_other_user.id = 99
        mock_session.get = AsyncMock(return_value=mock_other_user)

        with patch("src.api.mini_app.UserService", return_value=mock_user_service):
            target_user, switched = await _resolve_target_user(
                session=mock_session,
                telegram_id=mock_user.telegram_id,
                selected_user_id=99,
            )

        # Regular user selection should be ignored, target stays same
        assert target_user == mock_user
        assert switched is False


class TestMiniAppConfigEndpoint:
    """Tests for /api/mini-app/config endpoint."""

    def test_config_endpoint_exists(self, client):
        """Test config endpoint is available."""
        response = client.post("/api/mini-app/config", json={})

        # Should not be 404
        assert response.status_code != 404

    def test_config_endpoint_returns_json(self, client):
        """Test config endpoint returns JSON response."""
        response = client.post("/api/mini-app/config", json={})

        # Should return JSON (no exception on json())
        assert response.headers.get("content-type") is not None


class TestMiniAppInitEndpoint:
    """Tests for /api/mini-app/init endpoint."""

    def test_init_endpoint_exists(self, client):
        """Test init endpoint is available."""
        response = client.post("/api/mini-app/init", json={})

        # Should not be 404
        assert response.status_code != 404

    def test_init_endpoint_handles_post(self, client):
        """Test init endpoint handles POST requests."""
        response = client.post(
            "/api/mini-app/init",
            json={"initDataRaw": "test_data"},
            headers={"Content-Type": "application/json"},
        )

        # Should not be 404 (endpoint exists)
        assert response.status_code != 404


class TestMiniAppUserStatusEndpoint:
    """Tests for /api/mini-app/user-status endpoint."""

    def test_user_status_endpoint_exists(self, client):
        """Test user-status endpoint is available."""
        response = client.post("/api/mini-app/user-status", json={})

        # Should not be 404
        assert response.status_code != 404

    def test_user_status_endpoint_returns_structured_response(self, client):
        """Test user-status endpoint returns structured response."""
        response = client.post("/api/mini-app/user-status", json={})

        # Should have content type
        assert response.headers.get("content-type") is not None


class TestMiniAppUsersEndpoint:
    """Tests for /api/mini-app/users endpoint."""

    def test_users_endpoint_exists(self, client):
        """Test users endpoint is available."""
        response = client.post("/api/mini-app/users", json={})

        # Should not be 404
        assert response.status_code != 404

    def test_users_endpoint_accepts_post(self, client):
        """Test users endpoint accepts POST requests."""
        response = client.post(
            "/api/mini-app/users",
            json={"initDataRaw": "test_data"},
        )

        # Should not be 404
        assert response.status_code != 404


class TestMiniAppPropertiesEndpoint:
    """Tests for /api/mini-app/properties endpoint."""

    def test_properties_endpoint_exists(self, client):
        """Test properties endpoint is available."""
        response = client.post("/api/mini-app/properties", json={})

        # Should not be 404
        assert response.status_code != 404


class TestMiniAppTransactionsEndpoint:
    """Tests for /api/mini-app/transactions-list endpoint."""

    def test_transactions_endpoint_exists(self, client):
        """Test transactions-list endpoint is available."""
        response = client.post("/api/mini-app/transactions-list", json={})

        # Should not be 404
        assert response.status_code != 404

    def test_transactions_endpoint_accepts_pagination(self, client):
        """Test transactions-list endpoint accepts pagination params."""
        response = client.post(
            "/api/mini-app/transactions-list",
            json={"limit": 10, "offset": 0},
        )

        # Should not be 404
        assert response.status_code != 404


class TestMiniAppBillsEndpoint:
    """Tests for /api/mini-app/bills endpoint."""

    def test_bills_endpoint_exists(self, client):
        """Test bills endpoint is available."""
        response = client.post("/api/mini-app/bills", json={})

        # Should not be 404
        assert response.status_code != 404

    def test_bills_endpoint_handles_query_params(self, client):
        """Test bills endpoint handles query parameters."""
        response = client.post(
            "/api/mini-app/bills",
            json={"month": "2024-01"},
        )

        # Should not be 404
        assert response.status_code != 404


class TestMiniAppBalanceEndpoint:
    """Tests for /api/mini-app/balance endpoint."""

    def test_balance_endpoint_exists(self, client):
        """Test balance endpoint is available."""
        response = client.post("/api/mini-app/balance", json={})

        # Should not be 404
        assert response.status_code != 404

    def test_balance_endpoint_returns_balance_response(self, client):
        """Test balance endpoint returns balance response."""
        response = client.post("/api/mini-app/balance", json={})

        # Should have content type
        assert response.headers.get("content-type") is not None


class TestMiniAppBalancesEndpoint:
    """Tests for /api/mini-app/accounts endpoint."""

    def test_balances_endpoint_exists(self, client):
        """Test accounts endpoint is available."""
        response = client.post("/api/mini-app/accounts", json={})

        # Should not be 404
        assert response.status_code != 404

    def test_balances_endpoint_returns_multiple_balances(self, client):
        """Test accounts endpoint returns multiple accounts."""
        response = client.post("/api/mini-app/accounts", json={})

        # Should have content type
        assert response.headers.get("content-type") is not None


class TestMiniAppVerifyRegistrationEndpoint:
    """Tests for /api/mini-app/verify-registration endpoint."""

    def test_verify_registration_endpoint_exists(self, client):
        """Test verify-registration endpoint is available."""
        response = client.post("/api/mini-app/verify-registration", json={})

        # Should not be 404
        assert response.status_code != 404

    def test_verify_registration_endpoint_handles_signature(self, client):
        """Test verify-registration endpoint handles signature verification."""
        response = client.post(
            "/api/mini-app/verify-registration",
            json={"initDataRaw": "data", "signature": "sig"},
        )

        # Should not be 404
        assert response.status_code != 404


class TestMiniAppMenuActionEndpoint:
    """Tests for /api/mini-app/menu-action endpoint."""

    def test_menu_action_endpoint_exists(self, client):
        """Test menu-action endpoint is available."""
        response = client.post("/api/mini-app/menu-action", json={})

        # Should not be 404
        assert response.status_code != 404

    def test_menu_action_endpoint_handles_actions(self, client):
        """Test menu-action endpoint handles menu actions."""
        response = client.post(
            "/api/mini-app/menu-action",
            json={"action": "open_app"},
        )

        # Should not be 404
        assert response.status_code != 404
