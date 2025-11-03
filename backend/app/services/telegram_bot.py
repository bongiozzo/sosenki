"""
Telegram Bot service for sending notifications.

Handles:
- Admin group notifications when new requests arrive
- User notifications when requests are accepted/rejected
- Mock/in-memory transport for testing
"""

import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class NotificationTransport(ABC):
    """Abstract base class for notification transports."""

    @abstractmethod
    async def send_message(self, chat_id: int | str, message: str) -> bool:
        """Send a message to a Telegram chat.

        Args:
            chat_id: Telegram chat ID (int or group ID string)
            message: Message text to send

        Returns:
            bool: True if successful, False otherwise
        """
        pass


class MockTransport(NotificationTransport):
    """In-memory mock transport for testing.

    Stores all messages in memory instead of sending to Telegram.
    """

    def __init__(self):
        """Initialize with empty message log."""
        self.messages: list[Dict[str, Any]] = []

    async def send_message(self, chat_id: int | str, message: str) -> bool:
        """Store message in memory (mock behavior).

        Args:
            chat_id: Telegram chat ID
            message: Message text

        Returns:
            True (always succeeds in mock)
        """
        self.messages.append(
            {
                "chat_id": chat_id,
                "message": message,
            }
        )
        logger.debug(f"[MOCK] Message queued for {chat_id}: {message}")
        return True

    def get_messages(self, chat_id: Optional[int | str] = None) -> list[Dict[str, Any]]:
        """Retrieve stored messages, optionally filtered by chat_id.

        Args:
            chat_id: Optional filter by specific chat ID

        Returns:
            List of stored message dicts
        """
        if chat_id is None:
            return self.messages
        return [m for m in self.messages if m["chat_id"] == chat_id]

    def clear(self):
        """Clear all stored messages."""
        self.messages = []


class TelegramBotService:
    """Service for sending Telegram notifications.

    Uses a pluggable transport (real API or mock for testing).
    """

    def __init__(self, admin_chat_id: int | str, transport: Optional[NotificationTransport] = None):
        """Initialize Telegram bot service.

        Args:
            admin_chat_id: Telegram admin group chat ID for notifications
            transport: Optional transport (defaults to MockTransport for safety)
        """
        self.admin_chat_id = admin_chat_id
        self.transport = transport or MockTransport()

    async def notify_admin_new_request(
        self,
        telegram_id: int,
        first_name: str,
        last_name: Optional[str] = None,
        telegram_username: Optional[str] = None,
        note: Optional[str] = None,
    ) -> bool:
        """Send notification to admin group when new request arrives.

        Args:
            telegram_id: Telegram user ID from request
            first_name: User's first name
            last_name: User's last name
            telegram_username: User's @username (optional)
            note: Request note/comment (optional)

        Returns:
            bool: True if sent successfully
        """
        message_parts = [
            "📋 **New Access Request**",
            f"User: {first_name}",
        ]

        if last_name:
            message_parts.append(f"Last name: {last_name}")

        if telegram_username:
            message_parts.append(f"Username: @{telegram_username}")

        message_parts.append(f"Telegram ID: `{telegram_id}`")

        if note:
            message_parts.append(f"Note: {note}")

        message = "\n".join(message_parts)
        logger.info(
            f"Notifying admin group ({self.admin_chat_id}) about new request from {telegram_id}"
        )

        return await self.transport.send_message(self.admin_chat_id, message)

    async def notify_user_request_accepted(
        self,
        telegram_id: int,
        role: str,
    ) -> bool:
        """Send notification to user when their request is accepted.

        Args:
            telegram_id: User's Telegram ID
            role: Role assigned to user

        Returns:
            bool: True if sent successfully
        """
        message = (
            f"✅ Your access request has been approved! You've been granted the **{role}** role."
        )
        logger.info(f"Notifying user {telegram_id} of request acceptance (role: {role})")

        return await self.transport.send_message(telegram_id, message)

    async def notify_user_request_rejected(
        self,
        telegram_id: int,
        comment: Optional[str] = None,
    ) -> bool:
        """Send notification to user when their request is rejected.

        Args:
            telegram_id: User's Telegram ID
            comment: Optional comment from admin

        Returns:
            bool: True if sent successfully
        """
        message_parts = ["❌ Your access request has been declined."]

        if comment:
            message_parts.append(f"Reason: {comment}")

        message = " ".join(message_parts)
        logger.info(f"Notifying user {telegram_id} of request rejection")

        return await self.transport.send_message(telegram_id, message)


# Global service instance (would be initialized in main.py with real settings)
_service_instance: Optional[TelegramBotService] = None


def init_telegram_bot_service(
    admin_chat_id: int | str, transport: Optional[NotificationTransport] = None
):
    """Initialize global telegram bot service.

    Args:
        admin_chat_id: Admin group chat ID
        transport: Optional transport implementation
    """
    global _service_instance
    _service_instance = TelegramBotService(admin_chat_id, transport or MockTransport())


def get_telegram_bot_service() -> TelegramBotService:
    """Get the global telegram bot service instance.

    Returns:
        TelegramBotService: Global service instance (or creates with default mock)
    """
    global _service_instance
    if _service_instance is None:
        # Default to safe mock transport
        _service_instance = TelegramBotService(admin_chat_id=-1, transport=MockTransport())
    return _service_instance
