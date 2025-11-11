"""Notification service for sending Telegram messages."""

from telegram.ext import Application
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


class NotificationService:
    """Service for sending Telegram messages to clients and admins."""

    def __init__(self, app: Application):
        self.app = app
        self.bot = app.bot

    async def send_message(self, chat_id: str, text: str, reply_markup=None, parse_mode="HTML") -> None:
        """Send message to a Telegram chat.

        Args:
            chat_id: Telegram chat ID
            text: Message text
            reply_markup: Optional telegram reply_markup (InlineKeyboardMarkup etc.)
            parse_mode: Message parse mode (HTML or Markdown). Default: HTML for link support.
        """
        # T029: Send message via bot
        try:
            await self.bot.send_message(chat_id=int(chat_id), text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            print(f"Error sending message to {chat_id}: {e}")
            raise

    async def send_confirmation_to_client(
        self, client_id: str, message: str = None
    ) -> None:
        """Send confirmation message to client after request submission.

        Args:
            client_id: Client's Telegram ID
            message: Optional custom message (not used in MVP, using standard message)
        """
        # T029: Send standard confirmation message
        confirmation_text = (
            "Your request has been received and is pending review."
        )
        await self.send_message(client_id, confirmation_text)

    async def send_notification_to_admin(
        self, request_id: int, client_id: str, client_name: str = None, request_message: str = None
    ) -> None:
        """Send notification to admin about new request.

        Args:
            request_id: Request ID from database
            client_id: Client's Telegram ID
            client_name: Client's name from Telegram
            request_message: The client's request message
        """
        # Import here to avoid circular import
        from src.bot.config import bot_config
        from src.services import SessionLocal
        from src.models.user import User
        from sqlalchemy import select
        
        # T030: Send notification with [Approve] [Reject] reply keyboard
        # Include clickable link to client's Telegram profile so admin can chat with them
        client_profile_link = f"tg://user?id={client_id}"
        notification_text = (
            f"<b>Request #{request_id}</b>\n\n"
            f"<a href='{client_profile_link}'>{client_name or 'User'}</a> (ID: {client_id})\n\n"
            f"<b>Message:</b>\n{request_message or '(no message)'}\n\n"
        )
        
        # Get users without telegram_id to help admin identify who is requesting
        db = SessionLocal()
        try:
            users_without_telegram = db.execute(
                select(User).where(User.telegram_id.is_(None)).order_by(User.name)
            ).scalars().all()
            
            if users_without_telegram:
                notification_text += "<b>Users without Telegram ID:</b>\n"
                for user in users_without_telegram:
                    notification_text += f"{user.id}. {user.name}\n"
                notification_text += f"\nReply with user ID to approve and assign Telegram ID\n"
                notification_text += "Or use the buttons below:\n"
        finally:
            db.close()

        # Note: Reply keyboard implementation requires storing request_id
        # in the message context for admin handlers to parse.
        # For now, send the message. Admin handlers will need to track
        # which message replies correspond to which requests.

        # Provide inline buttons with callback_data so admin can approve/reject with a tap
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(text="✅ Approve", callback_data=f"approve:{request_id}"),
                    InlineKeyboardButton(text="❌ Reject", callback_data=f"reject:{request_id}"),
                ]
            ]
        )

        await self.send_message(bot_config.admin_telegram_id, notification_text, reply_markup=keyboard)

    async def send_welcome_message(self, client_id: str) -> None:
        """Send welcome message to approved client with Mini App button.

        Args:
            client_id: Client's Telegram ID
        """
        # Import here to avoid circular import
        from src.bot.config import bot_config
        
        # T041: Send welcome message after approval with Mini App button (US1)
        welcome_text = (
            "🎉 <b>Welcome to SOSenki!</b>\n\n"
            "Your request has been approved and access has been granted.\n\n"
            "Tap the button below to open the SOSenki app:"
        )
        
        # Add Mini App button if MINI_APP_URL is configured
        keyboard = None
        if bot_config.mini_app_url:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    text="📱 Open App",
                    web_app=WebAppInfo(url=bot_config.mini_app_url)
                )]
            ])
        
        await self.send_message(client_id, welcome_text, reply_markup=keyboard)

    async def send_rejection_message(self, client_id: str) -> None:
        """Send rejection message to rejected client.

        Args:
            client_id: Client's Telegram ID
        """
        # T050: Send rejection message after rejection
        rejection_text = (
            "Your request for access to SOSenki has not been approved at this time. "
            "Please contact support if you have questions."
        )
        await self.send_message(client_id, rejection_text)


__all__ = ["NotificationService"]
