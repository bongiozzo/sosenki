"""Unit tests for bot auth to increase coverage."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.services.auth_service import verify_bot_admin_authorization


class TestVerifyBotAdminAuthorization:
    """Tests for admin authorization verification."""

    @pytest.mark.asyncio
    async def test_verify_admin_authorization_success(self):
        """Test successful admin authorization."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_administrator = True

        with (
            patch(
                "src.services.auth_service.get_authenticated_user", new_callable=AsyncMock
            ) as mock_get_user,
            patch("src.services.AsyncSessionLocal") as mock_session_local,
        ):
            mock_get_user.return_value = mock_user
            mock_session_local.return_value.__aenter__.return_value = MagicMock()

            result = await verify_bot_admin_authorization(telegram_id=123)

            assert result == mock_user
            assert result.is_administrator is True

    @pytest.mark.asyncio
    async def test_verify_admin_authorization_non_admin(self):
        """Test non-admin user attempting admin operation."""
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.is_administrator = False

        with (
            patch(
                "src.services.auth_service.get_authenticated_user", new_callable=AsyncMock
            ) as mock_get_user,
            patch("src.services.AsyncSessionLocal") as mock_session_local,
        ):
            mock_get_user.return_value = mock_user
            mock_session_local.return_value.__aenter__.return_value = MagicMock()

            result = await verify_bot_admin_authorization(telegram_id=456)

            assert result is None

    @pytest.mark.asyncio
    async def test_verify_admin_authorization_not_found(self):
        """Test when user is not found (HTTPException 401)."""
        with (
            patch(
                "src.services.auth_service.get_authenticated_user", new_callable=AsyncMock
            ) as mock_get_user,
            patch("src.services.AsyncSessionLocal") as mock_session_local,
        ):
            mock_get_user.side_effect = HTTPException(status_code=401, detail="User not found")
            mock_session_local.return_value.__aenter__.return_value = MagicMock()

            result = await verify_bot_admin_authorization(telegram_id=999)

            assert result is None

    @pytest.mark.asyncio
    async def test_verify_admin_authorization_generic_exception(self):
        """Test handling of unexpected exceptions."""
        with (
            patch(
                "src.services.auth_service.get_authenticated_user", new_callable=AsyncMock
            ) as mock_get_user,
            patch("src.services.AsyncSessionLocal") as mock_session_local,
        ):
            mock_get_user.side_effect = RuntimeError("Unexpected database error")
            mock_session_local.return_value.__aenter__.return_value = MagicMock()

            result = await verify_bot_admin_authorization(telegram_id=789)

            assert result is None

    @pytest.mark.asyncio
    async def test_verify_admin_authorization_inactive_user(self):
        """Test when user exists but is inactive (HTTPException 401)."""
        with (
            patch(
                "src.services.auth_service.get_authenticated_user", new_callable=AsyncMock
            ) as mock_get_user,
            patch("src.services.AsyncSessionLocal") as mock_session_local,
        ):
            mock_get_user.side_effect = HTTPException(status_code=401, detail="User inactive")
            mock_session_local.return_value.__aenter__.return_value = MagicMock()

            result = await verify_bot_admin_authorization(telegram_id=111)

            assert result is None
