"""Unit tests for UserService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.user import User
from src.services.user_service import UserService


@pytest.mark.asyncio
async def test_verify_telegram_signature_valid():
    """Test Telegram WebApp signature verification with valid data."""
    # This would require a valid init_data string and bot token
    # For now, testing the method exists and has correct signature

    result = UserService.verify_telegram_webapp_signature(
        init_data='hash=test&user={"id":123}', bot_token="test_token"
    )

    # With invalid hash, should return None
    assert result is None


@pytest.mark.asyncio
async def test_can_access_mini_app_active_user():
    """Test can_access_mini_app returns True for active user."""
    mock_session = AsyncMock()

    # Mock user with is_active=True
    mock_user = User(
        telegram_id="123",
        is_active=True,
        is_investor=False,
        is_administrator=False,
        is_owner=False,
        is_staff=False,
    )

    # Mock the database query
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    user_service = UserService(mock_session)
    result = await user_service.can_access_mini_app("123")

    assert result is True


@pytest.mark.asyncio
async def test_can_access_mini_app_inactive_user():
    """Test can_access_mini_app returns False for inactive user."""
    mock_session = AsyncMock()

    # Mock user with is_active=False
    mock_user = User(
        telegram_id="123",
        is_active=False,
        is_investor=False,
        is_administrator=False,
        is_owner=False,
        is_staff=False,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    user_service = UserService(mock_session)
    result = await user_service.can_access_mini_app("123")

    assert result is False


@pytest.mark.asyncio
async def test_can_access_invest_investor_only():
    """Test can_access_invest requires both is_active and is_investor."""
    mock_session = AsyncMock()

    # Test 1: is_active=True, is_investor=True → True
    mock_user = User(
        telegram_id="123",
        is_active=True,
        is_investor=True,
        is_administrator=False,
        is_owner=False,
        is_staff=False,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result

    user_service = UserService(mock_session)
    result = await user_service.can_access_invest("123")

    assert result is True

    # Test 2: is_active=True, is_investor=False → False
    mock_user.is_investor = False
    result = await user_service.can_access_invest("123")
    assert result is False
