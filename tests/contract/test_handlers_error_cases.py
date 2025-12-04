"""Comprehensive error case tests for bot handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import delete
from telegram import Chat, Message, Update
from telegram import User as TelegramUser
from telegram.ext import ContextTypes

from src.bot.handlers import (
    handle_admin_callback,
    handle_admin_response,
    handle_request_command,
)
from src.models.user import User
from src.services import SessionLocal

# ============================================================================
# Fixtures
# ============================================================================


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


# ============================================================================
# handle_request_command Error Cases
# ============================================================================


class TestRequestCommandEdgeCases:
    """Test error and edge cases for /request command handler."""

    async def test_request_without_message_text(self, mock_telegram_user, mock_chat):
        """Test /request when update.message.text is None."""
        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.message.text = None
        update.message.from_user = mock_telegram_user
        update.message.chat = mock_chat

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        # Should return early without raising
        await handle_request_command(update, context)

    async def test_request_with_no_message(self):
        """Test /request when update.message is None."""
        update = MagicMock(spec=Update)
        update.message = None

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await handle_request_command(update, context)

    async def test_request_from_group_chat(self, mock_admin_user):
        """Test /request from a group chat (should be rejected)."""
        group_chat = Chat(id=-789, type="group")
        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.message.text = "/request test"
        update.message.from_user = mock_admin_user
        update.message.chat = group_chat
        update.message.reply_text = AsyncMock()

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        with patch("src.bot.config.bot_config"):
            await handle_request_command(update, context)

        # Should send rejection message
        update.message.reply_text.assert_called_once()

    async def test_request_from_supergroup_chat(self, mock_admin_user):
        """Test /request from a supergroup chat (should be rejected)."""
        supergroup_chat = Chat(id=-789, type="supergroup")
        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.message.text = "/request test"
        update.message.from_user = mock_admin_user
        update.message.chat = supergroup_chat
        update.message.reply_text = AsyncMock()

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        with patch("src.bot.config.bot_config"):
            await handle_request_command(update, context)

        update.message.reply_text.assert_called_once()

    async def test_request_user_already_has_access(self, mock_telegram_user, mock_chat):
        """Test /request from user who already has access."""
        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.message.text = "/request test"
        update.message.from_user = mock_telegram_user
        update.message.chat = mock_chat
        update.message.reply_text = AsyncMock()

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.application = AsyncMock()

        with patch("src.services.SessionLocal") as mock_session:
            with patch("src.bot.config.bot_config"):
                db_instance = MagicMock()
                mock_session.return_value = db_instance

                # User already exists and is active
                existing_user = MagicMock()
                existing_user.is_active = True
                existing_user.name = "Existing User"
                db_instance.execute.return_value.scalar_one_or_none.return_value = existing_user

                # Should execute without error (exercises code path)
                await handle_request_command(update, context)

    async def test_request_admin_notification_failure(self, mock_telegram_user, mock_chat):
        """Test /request when admin notification fails."""
        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.message.text = "/request test message"
        update.message.from_user = mock_telegram_user
        update.message.chat = mock_chat
        update.message.reply_text = AsyncMock()

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.application = AsyncMock()

        with patch("src.services.SessionLocal") as mock_session:
            with patch("src.bot.handlers.common.RequestService") as mock_req_service:
                with patch("src.bot.handlers.common.NotificationService") as mock_notif:
                    db_instance = MagicMock()
                    mock_session.return_value = db_instance
                    db_instance.execute.return_value.scalar_one_or_none.return_value = None

                    req_service_inst = AsyncMock()
                    mock_req_service.return_value = req_service_inst
                    req_service_inst.create_request.return_value = MagicMock(id=1)

                    notif_service_inst = AsyncMock()
                    mock_notif.return_value = notif_service_inst
                    notif_service_inst.send_confirmation_to_requester = AsyncMock()
                    # Admin notification fails
                    notif_service_inst.send_notification_to_admin = AsyncMock(
                        side_effect=Exception("Network error")
                    )

                    await handle_request_command(update, context)

                    # Should succeed despite admin notification failure
                    # (the exception is caught and logged)

    async def test_request_duplicate_pending_request(self, mock_telegram_user, mock_chat):
        """Test /request when duplicate pending request exists."""
        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.message.text = "/request test"
        update.message.from_user = mock_telegram_user
        update.message.chat = mock_chat
        update.message.reply_text = AsyncMock()

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.application = AsyncMock()

        with patch("src.services.SessionLocal") as mock_session:
            with patch("src.bot.handlers.common.RequestService") as mock_req_service:
                db_instance = MagicMock()
                mock_session.return_value = db_instance
                db_instance.execute.return_value.scalar_one_or_none.return_value = None

                req_service_inst = AsyncMock()
                mock_req_service.return_value = req_service_inst
                # Duplicate request returns None
                req_service_inst.create_request.return_value = None

                await handle_request_command(update, context)

                # Should inform user of pending request (message is in Russian from localizer)
                update.message.reply_text.assert_called_once()


# ============================================================================
# handle_admin_callback Error Cases
# ============================================================================


class TestAdminCallbackErrorCases:
    """Test error cases for admin callback handler."""

    async def test_callback_without_callback_query(self):
        """Test callback when callback_query is None."""
        update = MagicMock(spec=Update)
        update.callback_query = None

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await handle_admin_callback(update, context)

    async def test_callback_invalid_data_format(self):
        """Test callback with invalid data format."""
        cq = AsyncMock()
        cq.data = "invalid_format"
        cq.answer = AsyncMock()

        update = MagicMock(spec=Update)
        update.callback_query = cq

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await handle_admin_callback(update, context)

        cq.answer.assert_called_once()

    async def test_callback_invalid_request_id(self):
        """Test callback with non-integer request ID."""
        cq = AsyncMock()
        cq.data = "approve:not_a_number"
        cq.answer = AsyncMock()

        update = MagicMock(spec=Update)
        update.callback_query = cq

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await handle_admin_callback(update, context)

        cq.answer.assert_called_once()

    async def test_callback_request_not_found(self):
        """Test callback when request is not found."""
        cq = AsyncMock()
        cq.data = "approve:999"
        cq.from_user = TelegramUser(id=999999, is_bot=False, first_name="Admin")
        cq.answer = AsyncMock()

        update = MagicMock(spec=Update)
        update.callback_query = cq

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        with patch("src.services.SessionLocal") as mock_session:
            with patch("src.bot.handlers.admin_requests.AdminService") as mock_admin_service:
                db_instance = MagicMock()
                mock_session.return_value = db_instance

                admin_service_inst = AsyncMock()
                mock_admin_service.return_value = admin_service_inst
                admin_service_inst.approve_request.return_value = None

                await handle_admin_callback(update, context)

                cq.answer.assert_called_once()

    async def test_callback_unknown_action(self):
        """Test callback with unknown action."""
        cq = AsyncMock()
        cq.data = "unknown_action:123"
        cq.from_user = TelegramUser(id=999999, is_bot=False, first_name="Admin")
        cq.answer = AsyncMock()

        update = MagicMock(spec=Update)
        update.callback_query = cq

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        with patch("src.services.SessionLocal") as mock_session:
            db_instance = MagicMock()
            mock_session.return_value = db_instance

            await handle_admin_callback(update, context)

            # Should answer with error
            assert cq.answer.called


# ============================================================================
# handle_admin_response Error Cases
# ============================================================================


class TestAdminResponseErrorCases:
    """Test error cases for universal admin response handler."""

    @pytest.fixture(autouse=True)
    def cleanup_db(self):
        """Clean up and setup database before and after each test."""
        db = SessionLocal()
        try:
            db.execute(delete(User))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        # Setup: Create admin user for tests
        db = SessionLocal()
        try:
            admin1 = User(
                telegram_id=999999,
                name="Test Admin",
                is_active=True,
                is_administrator=True,
            )
            admin2 = User(
                telegram_id=999888777,
                name="Test Admin 2",
                is_active=True,
                is_administrator=True,
            )
            db.add(admin1)
            db.add(admin2)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        yield

        # Cleanup after test
        db = SessionLocal()
        try:
            db.execute(delete(User))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    async def test_admin_response_without_message(self):
        """Test response when update.message is None."""
        update = MagicMock(spec=Update)
        update.message = None

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await handle_admin_response(update, context)

    async def test_admin_response_without_reply_to_message(self, mock_admin_user, mock_chat):
        """Test response without replying to a message."""
        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.message.from_user = mock_admin_user
        update.message.chat = mock_chat
        update.message.text = "Approve"
        update.message.reply_to_message = None
        update.message.reply_text = AsyncMock()

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await handle_admin_response(update, context)

        update.message.reply_text.assert_called_once()

    async def test_admin_response_invalid_action(self, mock_admin_user, mock_chat):
        """Test response with invalid action."""
        original_message = MagicMock(spec=Message)
        original_message.text = "Request #123: Test"

        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.message.from_user = mock_admin_user
        update.message.chat = mock_chat
        update.message.text = "invalid_action"
        update.message.reply_to_message = original_message
        update.message.reply_text = AsyncMock()

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await handle_admin_response(update, context)

        update.message.reply_text.assert_called_once()

    async def test_admin_response_numeric_user_id_approval(self, mock_admin_user, mock_chat):
        """Test numeric user ID selection for approval."""
        original_message = MagicMock(spec=Message)
        original_message.text = "Request #123: Test"

        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.message.from_user = mock_admin_user
        update.message.chat = mock_chat
        update.message.text = "456789"  # Numeric user ID
        update.message.reply_to_message = original_message
        update.message.reply_text = AsyncMock()

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.application = AsyncMock()

        with patch("src.services.SessionLocal") as mock_session:
            with patch("src.bot.handlers.admin_requests.AdminService") as mock_admin_service:
                with patch("src.bot.handlers.common.NotificationService"):
                    db_instance = MagicMock()
                    mock_session.return_value = db_instance

                    admin_service_inst = AsyncMock()
                    mock_admin_service.return_value = admin_service_inst
                    admin_service_inst.approve_request.return_value = MagicMock(
                        id=123, user_telegram_id=999
                    )

                    await handle_admin_response(update, context)

                    # Should call approve with selected_user_id
                    call_args = admin_service_inst.approve_request.call_args
                    assert call_args[1]["selected_user_id"] == 456789

    async def test_admin_response_database_error(self, mock_admin_user, mock_chat):
        """Test response when database error occurs."""
        original_message = MagicMock(spec=Message)
        original_message.text = "Request #123: Test"

        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.message.from_user = mock_admin_user
        update.message.chat = mock_chat
        update.message.text = "Approve"
        update.message.reply_to_message = original_message
        update.message.reply_text = AsyncMock()

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        with patch("src.services.SessionLocal") as mock_session:
            with patch("src.bot.handlers.admin_requests.AdminService") as mock_admin_service:
                db_instance = MagicMock()
                mock_session.return_value = db_instance

                admin_service_inst = AsyncMock()
                mock_admin_service.return_value = admin_service_inst
                admin_service_inst.approve_request.side_effect = Exception("DB Error")

                await handle_admin_response(update, context)

                update.message.reply_text.assert_called_once()
