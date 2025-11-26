"""Tests for bot handlers - command and callback processing."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Chat, Message, Update
from telegram import User as TelegramUser
from telegram.ext import ContextTypes

from src.bot.handlers import (
    handle_admin_approve,
    handle_admin_callback,
    handle_admin_reject,
    handle_admin_response,
    handle_request_command,
)


# Fixtures for common test objects
@pytest.fixture
def mock_telegram_user():
    """Create a mock Telegram user."""
    return TelegramUser(id=123456, is_bot=False, first_name="Test", last_name="User")


@pytest.fixture
def mock_admin_user():
    """Create a mock admin Telegram user."""
    return TelegramUser(id=999999, is_bot=False, first_name="Admin", username="admin_user")


@pytest.fixture
def mock_chat():
    """Create a mock chat (private)."""
    return Chat(id=123456, type="private")


@pytest.fixture
def mock_group_chat():
    """Create a mock group chat."""
    return Chat(id=-789, type="group")


@pytest.fixture
def mock_message(mock_telegram_user, mock_chat):
    """Create a mock message."""
    return Message(
        message_id=1,
        date=1234567890,
        chat=mock_chat,
        from_user=mock_telegram_user,
    )


@pytest.fixture
def mock_context():
    """Create a mock context."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.application = AsyncMock()
    return context


@pytest.fixture
def mock_update(mock_message):
    """Create a mock update."""
    update = MagicMock(spec=Update)
    update.message = mock_message
    return update


class TestHandleRequestCommand:
    """Tests for handle_request_command handler."""

    @pytest.mark.asyncio
    async def test_handle_request_no_message(self, mock_context):
        """Test request handler with no message text."""
        update = MagicMock(spec=Update)
        update.message = None

        await handle_request_command(update, mock_context)
        # Should return early without error

    @pytest.mark.asyncio
    async def test_handle_request_from_group_chat(self, mock_context):
        """Test request handler rejects group chat requests."""
        message = MagicMock(spec=Message)
        message.text = "/request test message"
        message.chat.type = "group"
        message.from_user = MagicMock()
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message

        with patch("src.bot.handlers.SessionLocal"):
            with patch("src.bot.config.bot_config"):
                await handle_request_command(update, mock_context)
                message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_request_from_supergroup_chat(self, mock_context):
        """Test request handler rejects supergroup chat requests."""
        message = MagicMock(spec=Message)
        message.text = "/request test message"
        message.chat.type = "supergroup"
        message.from_user = MagicMock()
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message

        with patch("src.bot.handlers.SessionLocal"):
            with patch("src.bot.config.bot_config"):
                await handle_request_command(update, mock_context)
                message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_request_with_username(self, mock_context):
        """Test request handler with user having username."""
        message = MagicMock(spec=Message)
        message.text = "/request Please review my request"
        message.chat.type = "private"
        message.from_user = MagicMock()
        message.from_user.id = 123
        message.from_user.username = "testuser"
        message.from_user.first_name = "Test"
        message.from_user.last_name = None
        message.from_user.phone_number = None
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message

        # Use MagicMock (not AsyncMock) for db since db.close() is synchronous
        mock_db = MagicMock()
        mock_db.execute = MagicMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        with patch("src.bot.handlers.SessionLocal", return_value=mock_db):
            with patch("src.bot.handlers.RequestService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service.store_request = AsyncMock(return_value=MagicMock())
                mock_service_class.return_value = mock_service

                with patch("src.bot.handlers.NotificationService"):
                    await handle_request_command(update, mock_context)

    @pytest.mark.asyncio
    async def test_handle_request_with_first_and_last_name(self, mock_context):
        """Test request handler with user having first and last name."""
        message = MagicMock(spec=Message)
        message.text = "/request test message"
        message.chat.type = "private"
        message.from_user = MagicMock()
        message.from_user.id = 123
        message.from_user.username = None
        message.from_user.first_name = "John"
        message.from_user.last_name = "Doe"
        message.from_user.phone_number = None
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message

        # Use MagicMock (not AsyncMock) for db since db.close() is synchronous
        mock_db = MagicMock()
        mock_db.execute = MagicMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        with patch("src.bot.handlers.SessionLocal", return_value=mock_db):
            with patch("src.bot.handlers.RequestService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service.store_request = AsyncMock(return_value=MagicMock())
                mock_service_class.return_value = mock_service

                with patch("src.bot.handlers.NotificationService"):
                    await handle_request_command(update, mock_context)

    @pytest.mark.asyncio
    async def test_handle_request_with_phone_number(self, mock_context):
        """Test request handler with user having phone number."""
        message = MagicMock(spec=Message)
        message.text = "/request"
        message.chat.type = "private"
        message.from_user = MagicMock()
        message.from_user.id = 123
        message.from_user.username = None
        message.from_user.first_name = None
        message.from_user.last_name = None
        message.from_user.phone_number = "+1234567890"
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message

        # Use MagicMock (not AsyncMock) for db since db.close() is synchronous
        mock_db = MagicMock()
        mock_db.execute = MagicMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        with patch("src.bot.handlers.SessionLocal", return_value=mock_db):
            with patch("src.bot.handlers.RequestService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service.store_request = AsyncMock(return_value=MagicMock())
                mock_service_class.return_value = mock_service

                with patch("src.bot.handlers.NotificationService"):
                    await handle_request_command(update, mock_context)

    @pytest.mark.asyncio
    async def test_handle_request_active_user_exists(self, mock_context):
        """Test request handler when active user already exists."""
        message = MagicMock(spec=Message)
        message.text = "/request test message"
        message.chat.type = "private"
        message.from_user = MagicMock()
        message.from_user.id = 123
        message.from_user.username = "testuser"
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message

        mock_existing_user = MagicMock()
        mock_existing_user.is_active = True
        mock_existing_user.name = "Test User"

        # Use MagicMock (not AsyncMock) for db since db.close() is synchronous
        mock_db = MagicMock()
        mock_db.execute = MagicMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_existing_user))
        )

        with patch("src.bot.handlers.SessionLocal", return_value=mock_db):
            with patch("src.bot.config.bot_config"):
                await handle_request_command(update, mock_context)


class TestHandleAdminApprove:
    """Tests for handle_admin_approve handler."""

    @pytest.mark.asyncio
    async def test_handle_approve_no_message(self, mock_context):
        """Test approve handler with no message."""
        update = MagicMock(spec=Update)
        update.message = None

        await handle_admin_approve(update, mock_context)
        # Should return early without error

    @pytest.mark.asyncio
    async def test_handle_approve_no_user(self, mock_context):
        """Test approve handler with no user info."""
        update = MagicMock(spec=Update)
        message = MagicMock(spec=Message)
        message.from_user = None
        update.message = message

        await handle_admin_approve(update, mock_context)
        # Should return early without error

    @pytest.mark.asyncio
    async def test_handle_approve_non_approval_text(self, mock_context):
        """Test approve handler with non-approval text."""
        message = MagicMock(spec=Message)
        message.text = "Random text"
        message.from_user = MagicMock()
        message.from_user.id = 999
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message

        await handle_admin_approve(update, mock_context)
        message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_approve_no_reply_to_message(self, mock_context):
        """Test approve handler without reply_to_message."""
        message = MagicMock(spec=Message)
        message.text = "Approve"
        message.from_user = MagicMock()
        message.from_user.id = 999
        message.reply_to_message = None
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message

        await handle_admin_approve(update, mock_context)
        message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_approve_invalid_request_id_format(self, mock_context):
        """Test approve handler with invalid request ID format."""
        reply_message = MagicMock(spec=Message)
        reply_message.text = "Some random notification without ID"

        message = MagicMock(spec=Message)
        message.text = "Approve"
        message.from_user = MagicMock()
        message.from_user.id = 999
        message.reply_to_message = reply_message
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message

        await handle_admin_approve(update, mock_context)
        message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_approve_request_not_found(self, mock_context):
        """Test approve handler when request not found."""
        reply_message = MagicMock(spec=Message)
        reply_message.text = "Request #123: John Doe"

        message = MagicMock(spec=Message)
        message.text = "Approve"
        message.from_user = MagicMock()
        message.from_user.id = 999
        message.from_user.first_name = "Admin"
        message.reply_to_message = reply_message
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message

        # Use MagicMock (not AsyncMock) for db since db.close() is synchronous
        mock_db = MagicMock()
        with patch("src.bot.handlers.SessionLocal", return_value=mock_db):
            with patch("src.bot.handlers.AdminService") as mock_service_class:
                mock_service = MagicMock()
                mock_service.approve_request = AsyncMock(return_value=None)
                mock_service_class.return_value = mock_service

                await handle_admin_approve(update, mock_context)
                message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_approve_success(self, mock_context):
        """Test successful approval."""
        reply_message = MagicMock(spec=Message)
        reply_message.text = "Request #123: John Doe (Client ID: 456)"

        message = MagicMock(spec=Message)
        message.text = "Approve"
        message.from_user = MagicMock()
        message.from_user.id = 999
        message.from_user.first_name = "Admin"
        message.reply_to_message = reply_message
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message

        mock_request = MagicMock()
        mock_request.user_telegram_id = "456"

        # Use MagicMock (not AsyncMock) for db since db.close() is synchronous
        mock_db = MagicMock()
        with patch("src.bot.handlers.SessionLocal", return_value=mock_db):
            with patch("src.bot.handlers.AdminService") as mock_service_class:
                mock_service = MagicMock()
                mock_service.approve_request = AsyncMock(return_value=mock_request)
                mock_service_class.return_value = mock_service

                with patch("src.bot.handlers.NotificationService") as mock_notif_class:
                    mock_notif = AsyncMock()
                    mock_notif.send_welcome_message = AsyncMock()
                    mock_notif_class.return_value = mock_notif

                    await handle_admin_approve(update, mock_context)
                    message.reply_text.assert_called_once()


class TestHandleAdminReject:
    """Tests for handle_admin_reject handler."""

    @pytest.mark.asyncio
    async def test_handle_reject_no_message(self, mock_context):
        """Test reject handler with no message."""
        update = MagicMock(spec=Update)
        update.message = None

        await handle_admin_reject(update, mock_context)
        # Should return early without error

    @pytest.mark.asyncio
    async def test_handle_reject_non_rejection_text(self, mock_context):
        """Test reject handler with non-rejection text."""
        message = MagicMock(spec=Message)
        message.text = "Random text"
        message.from_user = MagicMock()
        message.from_user.id = 999
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message

        await handle_admin_reject(update, mock_context)
        message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_reject_no_reply_to_message(self, mock_context):
        """Test reject handler without reply_to_message."""
        message = MagicMock(spec=Message)
        message.text = "Reject"
        message.from_user = MagicMock()
        message.from_user.id = 999
        message.reply_to_message = None
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message

        await handle_admin_reject(update, mock_context)
        message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_reject_success(self, mock_context):
        """Test successful rejection."""
        reply_message = MagicMock(spec=Message)
        reply_message.text = "Request #456: Jane Smith (Client ID: 789)"

        message = MagicMock(spec=Message)
        message.text = "Reject"
        message.from_user = MagicMock()
        message.from_user.id = 999
        message.from_user.first_name = "Admin"
        message.reply_to_message = reply_message
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message

        mock_request = MagicMock()
        mock_request.user_telegram_id = "789"

        # Use MagicMock (not AsyncMock) for db since db.close() is synchronous
        mock_db = MagicMock()
        with patch("src.bot.handlers.SessionLocal", return_value=mock_db):
            with patch("src.bot.handlers.AdminService") as mock_service_class:
                mock_service = MagicMock()
                mock_service.reject_request = AsyncMock(return_value=mock_request)
                mock_service_class.return_value = mock_service

                with patch("src.bot.handlers.NotificationService") as mock_notif_class:
                    mock_notif = AsyncMock()
                    mock_notif.send_rejection_message = AsyncMock()
                    mock_notif_class.return_value = mock_notif

                    await handle_admin_reject(update, mock_context)
                    message.reply_text.assert_called_once()


class TestHandleAdminResponse:
    """Tests for handle_admin_response handler."""

    @pytest.mark.asyncio
    async def test_handle_response_no_message(self, mock_context):
        """Test response handler with no message."""
        update = MagicMock(spec=Update)
        update.message = None

        await handle_admin_response(update, mock_context)
        # Should return early without error

    @pytest.mark.asyncio
    async def test_handle_response_extract_message(self, mock_context):
        """Test response handler extracts message correctly."""
        message = MagicMock(spec=Message)
        message.text = "/response Response text here"
        message.from_user = MagicMock()
        message.from_user.id = 999
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message

        mock_db = AsyncMock()
        with patch("src.bot.handlers.SessionLocal", return_value=mock_db):
            await handle_admin_response(update, mock_context)


class TestHandleAdminCallback:
    """Tests for handle_admin_callback handler."""

    @pytest.mark.asyncio
    async def test_handle_callback_no_query(self, mock_context):
        """Test callback handler with no query."""
        update = MagicMock(spec=Update)
        update.callback_query = None

        await handle_admin_callback(update, mock_context)
        # Should return early without error

    @pytest.mark.asyncio
    async def test_handle_callback_with_button_action(self, mock_context):
        """Test callback handler with button action."""
        query = MagicMock()
        query.from_user = MagicMock()
        query.from_user.id = 999
        query.data = "approve_123"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.callback_query = query

        mock_db = AsyncMock()
        with patch("src.bot.handlers.SessionLocal", return_value=mock_db):
            with patch("src.bot.handlers.AdminService"):
                await handle_admin_callback(update, mock_context)
