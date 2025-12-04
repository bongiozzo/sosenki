"""Notification service for sending Telegram messages."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application

from src.services.localizer import t


class NotificationService:
    """Service for sending Telegram messages to clients and admins."""

    def __init__(self, app: Application):
        self.app = app
        self.bot = app.bot

    async def send_message(
        self, chat_id: str, text: str, reply_markup=None, parse_mode="HTML"
    ) -> None:
        """Send message to a Telegram chat.

        Args:
            chat_id: Telegram chat ID
            text: Message text
            reply_markup: Optional telegram reply_markup (InlineKeyboardMarkup etc.)
            parse_mode: Message parse mode (HTML or Markdown). Default: HTML for link support.
        """
        # T029: Send message via bot
        try:
            await self.bot.send_message(
                chat_id=int(chat_id), text=text, reply_markup=reply_markup, parse_mode=parse_mode
            )
        except Exception as e:
            print(f"Error sending message to {chat_id}: {e}")
            raise

    async def send_confirmation_to_requester(self, requester_id: str, message: str = None) -> None:
        """Send confirmation message to requester after request submission.

        Args:
            requester_id: Requester's Telegram ID
            message: Optional custom message (not used in MVP, using standard message)
        """
        # T029: Send standard confirmation message
        await self.send_message(requester_id, t("status.pending"))

    async def send_notification_to_admin(
        self,
        request_id: int,
        requester_id: str,
        requester_username: str = None,
        request_message: str = None,
    ) -> None:
        """Send notification to admin about new request.

        Args:
            request_id: Request ID from database
            requester_id: Requester's Telegram ID
            requester_username: Requester's identifier (username, name, phone, or ID)
            request_message: The requester's request message
        """
        # Import here to avoid circular import
        from sqlalchemy import select

        from src.models.user import User
        from src.services import SessionLocal
        from src.services.admin_utils import get_admin_telegram_id

        db = SessionLocal()
        try:
            # Get admin telegram ID from database
            admin_telegram_id = get_admin_telegram_id(db)
            if not admin_telegram_id:
                raise ValueError("No admin user found in database")

            # T030: Send notification with [Approve] [Reject] reply keyboard
            # Include clickable link to requester's Telegram profile so admin can chat with them
            notification_text = t(
                "admin.admin_notification_request",
                request_id=request_id,
                requester_id=requester_id,
                requester_username=requester_username,
                request_message=request_message or "(no message)",
            )
            # Get users without telegram_id or inactive to help admin identify who is requesting
            users_without_telegram = (
                db.execute(
                    select(User)
                    .where((User.telegram_id.is_(None)) | (~User.is_active))
                    .order_by(User.name)
                )
                .scalars()
                .all()
            )

            if users_without_telegram:
                notification_text += t("admin.admin_users_without_telegram")
                for user in users_without_telegram:
                    notification_text += f"{user.id}. {user.name}\n"
                notification_text += t("admin.admin_reply_with_id")
                notification_text += t("admin.admin_or_use_buttons")

            # Note: Reply keyboard implementation requires storing request_id
            # in the message context for admin handlers to parse.
            # For now, send the message. Admin handlers will need to track
            # which message replies correspond to which requests.

            # Provide inline buttons with callback_data so admin can approve/reject with a tap
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=t("buttons.approve"), callback_data=f"approve:{request_id}"
                        ),
                        InlineKeyboardButton(
                            text=t("buttons.reject"), callback_data=f"reject:{request_id}"
                        ),
                    ]
                ]
            )

            await self.send_message(admin_telegram_id, notification_text, reply_markup=keyboard)
        finally:
            db.close()

    async def send_welcome_message(self, requester_id: str) -> None:
        """Send welcome message to approved requester with Mini App button.

        Args:
            requester_id: Requester's Telegram ID
        """
        # Import here to avoid circular import
        from src.bot.config import bot_config

        # T041: Send welcome message after approval with Mini App button (US1)
        welcome_text = t("admin.welcome_message")

        # Add Mini App button if MINI_APP_URL is configured
        keyboard = None
        if bot_config.mini_app_url:
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=t("buttons.open_app"),
                            web_app=WebAppInfo(url=bot_config.mini_app_url),
                        )
                    ]
                ]
            )

        await self.send_message(requester_id, welcome_text, reply_markup=keyboard)

    async def send_rejection_message(self, requester_id: str) -> None:
        """Send rejection message to rejected requester.

        Args:
            requester_id: Requester's Telegram ID
        """
        # T050: Send rejection message after rejection
        await self.send_message(requester_id, t("admin.rejection_message"))


__all__ = ["NotificationService"]
