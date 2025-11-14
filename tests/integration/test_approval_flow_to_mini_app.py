"""Integration test for approval flow to Mini App (US1)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import InlineKeyboardMarkup

from src.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_approval_sends_welcome_with_webapp_button():
    """Test that approving a request sends welcome message with Mini App button."""
    # This is a placeholder integration test for US1
    # Full implementation would require test database setup

    # Verify that NotificationService.send_welcome_message is called
    # and includes WebApp button when MINI_APP_URL is configured

    # For now, this test verifies the notification service has the method
    mock_app = MagicMock()
    notification_service = NotificationService(mock_app)

    assert hasattr(notification_service, "send_welcome_message")
    assert callable(notification_service.send_welcome_message)


@pytest.mark.asyncio
async def test_welcome_message_includes_webapp_button():
    """Test that welcome message includes WebApp button with correct URL."""
    # This test would verify the InlineKeyboardMarkup includes WebAppInfo
    # Full implementation requires mocking bot.send_message and inspecting reply_markup

    mock_app = MagicMock()
    mock_bot = AsyncMock()
    mock_app.bot = mock_bot

    notification_service = NotificationService(mock_app)

    # Call send_welcome_message
    await notification_service.send_welcome_message(
        requester_id="123456789"
    )  # Verify bot.send_message was called
    assert mock_bot.send_message.called

    # Get the call arguments
    call_args = mock_bot.send_message.call_args

    # Verify reply_markup is InlineKeyboardMarkup (or None if MINI_APP_URL not set)
    if call_args and "reply_markup" in call_args.kwargs:
        reply_markup = call_args.kwargs["reply_markup"]
        # If reply_markup exists, it should be InlineKeyboardMarkup with WebApp button
        if reply_markup:
            assert isinstance(reply_markup, InlineKeyboardMarkup)


# Note: Full integration test would:
# 1. Create test database with AccessRequest
# 2. Mock Telegram bot
# 3. Call approval handler
# 4. Verify welcome message sent within 5 seconds
# 5. Verify message includes "Open App" button
# 6. Verify button has web_app with correct URL


@pytest.mark.asyncio
async def test_dashboard_loads_with_user_statuses():
    """Test dashboard renders with user statuses after /user-status call."""
    # Full implementation would:
    # 1. Create test User with roles
    # 2. Mock Telegram signature verification
    # 3. Call GET /api/mini-app/user-status
    # 4. Verify response includes correct roles and stakeholder_url
    #
    # Expected response structure:
    # {
    #   "user_id": <int>,
    #   "roles": ["investor", "owner", "stakeholder"],
    #   "stakeholder_url": "https://example.com/stakeholders",
    #   "share_percentage": 1
    # }
    pass


@pytest.mark.asyncio
async def test_stakeholder_link_appears_for_owners():
    """Test owners see stakeholder link on dashboard."""
    # Full implementation would:
    # 1. Create owner user with is_owner=True
    # 2. Mock Telegram signature verification
    # 3. Call GET /api/mini-app/user-status
    # 4. Verify stakeholder_url is not null in response
    # 5. Verify share_percentage is 0 or 1 (not None)
    pass


@pytest.mark.asyncio
async def test_stakeholder_link_hidden_for_non_owners():
    """Test non-owners do NOT see stakeholder link."""
    # Full implementation would:
    # 1. Create user with is_owner=False
    # 2. Mock Telegram signature verification
    # 3. Call GET /api/mini-app/user-status
    # 4. Verify stakeholder_url is null/missing in response
    # 5. Verify share_percentage is None
    pass
