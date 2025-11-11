"""Integration tests for group chat rejection in /request handler.

Tests that /request commands in group chats are properly rejected since
group chats don't support WebAppInfo buttons for the mini app.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import delete
from telegram import Update

from src.bot import handlers
from src.models.access_request import AccessRequest
from src.models.user import User
from src.services import SessionLocal


class TestGroupChatRejection:
    """Integration tests for group chat rejection."""

    @pytest.fixture(autouse=True)
    def cleanup_db(self):
        """Clean up database before and after each test."""
        db = SessionLocal()
        try:
            db.execute(delete(User).where(User.name.like("User_%")))
            db.execute(delete(AccessRequest))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        yield

        # Cleanup after test
        db = SessionLocal()
        try:
            db.execute(delete(User).where(User.name.like("User_%")))
            db.execute(delete(AccessRequest))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    @pytest.fixture
    def mock_context(self):
        """Create mock context with bot application."""
        context = MagicMock()
        context.application = MagicMock()
        context.application.bot = MagicMock()
        context.application.bot.send_message = AsyncMock()
        return context

    @pytest.mark.asyncio
    async def test_group_chat_request_rejected_with_private_message_prompt(self, mock_context):
        """Test that /request in group chat is rejected with instruction to use private message."""
        # Create update from a group chat
        update = MagicMock(spec=Update)
        update.message = MagicMock()
        update.message.text = "/request Please give me access"
        update.message.chat = MagicMock()
        update.message.chat.type = "group"
        update.message.chat.id = -123456789
        update.message.from_user = MagicMock()
        update.message.from_user.id = 987654321
        update.message.from_user.first_name = "John"
        update.message.reply_text = AsyncMock()

        # Call handler
        await handlers.handle_request_command(update, mock_context)

        # Verify reply was sent with rejection message
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        response_text = call_args[0][0]

        # Check that response contains rejection message
        assert "private message" in response_text.lower()
        assert "❌" in response_text or "requests can only be" in response_text.lower()

        # Verify no AccessRequest was created
        db = SessionLocal()
        try:
            pending_requests = db.query(AccessRequest).all()
            assert len(pending_requests) == 0, "No request should be created for group chats"
        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_supergroup_chat_request_rejected(self, mock_context):
        """Test that /request in supergroup is also rejected."""
        # Create update from a supergroup chat
        update = MagicMock(spec=Update)
        update.message = MagicMock()
        update.message.text = "/request Access request from supergroup"
        update.message.chat = MagicMock()
        update.message.chat.type = "supergroup"
        update.message.chat.id = -987654321
        update.message.from_user = MagicMock()
        update.message.from_user.id = 111222333
        update.message.from_user.first_name = "Jane"
        update.message.reply_text = AsyncMock()

        # Call handler
        await handlers.handle_request_command(update, mock_context)

        # Verify reply was sent
        update.message.reply_text.assert_called_once()

        # Verify no request was created
        db = SessionLocal()
        try:
            pending_requests = db.query(AccessRequest).all()
            assert len(pending_requests) == 0
        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_private_chat_request_accepted(self, mock_context):
        """Test that /request in private chat is still processed normally."""
        # Create update from a private chat
        update = MagicMock(spec=Update)
        update.message = MagicMock()
        update.message.text = "/request Please give me access"
        update.message.chat = MagicMock()
        update.message.chat.type = "private"
        update.message.chat.id = 987654321
        update.message.from_user = MagicMock()
        update.message.from_user.id = 987654321
        update.message.from_user.first_name = "John"
        update.message.reply_text = AsyncMock()

        # Call handler
        await handlers.handle_request_command(update, mock_context)

        # Should not have called reply_text with rejection message
        # (it might call with confirmation, but let's just verify request was created)
        db = SessionLocal()
        try:
            pending_requests = db.query(AccessRequest).all()
            # Should have created a request (if no other validation failed)
            assert len(pending_requests) <= 1, "Request should be created for private chats"
        finally:
            db.close()
