"""Notification service for sending Telegram messages."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application

from src.models.account import Account, AccountType
from src.models.user import User
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
        await self.send_message(requester_id, t("status_pending"))

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
                "msg_admin_notification",
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
                notification_text += t("msg_admin_users_without_telegram")
                for user in users_without_telegram:
                    notification_text += f"{user.id}. {user.name}\n"
                notification_text += t("msg_admin_reply_with_id")
                notification_text += t("msg_admin_or_use_buttons")

            # Note: Reply keyboard implementation requires storing request_id
            # in the message context for admin handlers to parse.
            # For now, send the message. Admin handlers will need to track
            # which message replies correspond to which requests.

            # Provide inline buttons with callback_data so admin can approve/reject with a tap
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=t("btn_approve"), callback_data=f"approve:{request_id}"
                        ),
                        InlineKeyboardButton(
                            text=t("btn_reject"), callback_data=f"reject:{request_id}"
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
        welcome_text = t("msg_admin_welcome")

        # Add Mini App button if MINI_APP_URL is configured
        keyboard = None
        if bot_config.mini_app_url:
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=t("btn_open_app"),
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
        await self.send_message(requester_id, t("msg_admin_rejection"))

    async def notify_account_owners_and_representatives(
        self,
        session,
        account_ids: list[int],
        text: str,
        skip_telegram_id: int | None = None,
    ) -> None:
        """Notify owners and their representatives for the given accounts.

        Filters recipients to active users with telegram_id, and deduplicates
        by telegram_id. Optionally skips a specific telegram_id (e.g., the
        initiating admin).
        """
        if not account_ids:
            return

        account_result = await session.execute(
            select(Account)
            .options(selectinload(Account.user))
            .where(Account.id.in_(account_ids), Account.account_type == AccountType.OWNER)
        )
        owner_users = [
            account.user
            for account in account_result.scalars()
            if account.user and account.user.is_active and account.user.telegram_id
        ]

        owner_ids = {user.id for user in owner_users}
        if not owner_ids:
            return

        reps_result = await session.execute(
            select(User).where(
                User.representative_id.in_(owner_ids),
                User.is_active.is_(True),
                User.telegram_id.isnot(None),
            )
        )
        representatives = reps_result.scalars().all()

        seen: set[int] = set()
        recipients = [*owner_users, *representatives]
        for user in recipients:
            if not user.telegram_id or user.telegram_id == skip_telegram_id:
                continue
            if user.telegram_id in seen:
                continue
            seen.add(user.telegram_id)
            await self.send_message(chat_id=user.telegram_id, text=text)


__all__ = ["NotificationService"]
