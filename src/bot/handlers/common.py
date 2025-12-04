"""Common bot handlers: /start and /request commands."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes

from src.services import SessionLocal, UserServiceSync
from src.services.localizer import t
from src.services.notification_service import NotificationService
from src.services.request_service import RequestService

logger = logging.getLogger(__name__)


async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command.

    Sends welcome message to user.
    """
    try:
        if not update.message:
            logger.warning("Received /start without message")
            return

        await update.message.reply_text(t("labels.welcome"))
        logger.info("Sent welcome message to user %s", update.message.from_user.id)

    except Exception as e:
        logger.error("Error in start command handler: %s", e, exc_info=True)


async def handle_request_command(  # noqa: C901
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /request command from client.

    Parses message, validates no pending request exists, stores request,
    sends confirmation to client and notification to admin.

    T031, T034, T035: Implement request handler with logging and error handling

    /request can be sent with or without a message:
    - /request                   -> submits request with no message
    - /request Some message text -> submits request with message text
    """
    try:
        # Extract message parts
        if not update.message or not update.message.text:
            logger.warning("Received /request without message text")
            return

        # Check if message is from a group chat (group chats don't support WebAppInfo buttons)
        if update.message.chat.type in ["group", "supergroup"]:
            logger.info(
                "Received /request from group chat %s, rejecting with private message prompt",
                update.message.chat.id,
            )

            from src.bot.config import bot_config

            await update.message.reply_text(
                t("errors.group_chat_error", bot_name=bot_config.telegram_bot_name)
            )
            return

        # Parse: /request [message] (message is optional)
        text_parts = update.message.text.split(maxsplit=1)
        request_message = text_parts[1] if len(text_parts) > 1 else ""

        requester_id = update.message.from_user.id

        # Build requester identifier: prefer username, then first+last name, then phone, then user_id
        if update.message.from_user.username:
            requester_username = update.message.from_user.username
        elif update.message.from_user.first_name:
            if update.message.from_user.last_name:
                requester_username = (
                    f"{update.message.from_user.first_name} {update.message.from_user.last_name}"
                )
            else:
                requester_username = update.message.from_user.first_name
        elif update.message.from_user.phone_number:
            requester_username = update.message.from_user.phone_number
        else:
            requester_username = requester_id

        # T034: Log request submission attempt
        logger.info(
            "Processing /request from requester %s: %s",
            requester_id,
            request_message[:50] if request_message else "(no message)",
        )

        # T028: Use RequestService to create request (validates no duplicate)
        db = SessionLocal()
        try:
            # Check if user already exists with this telegram_id and is active
            user_service = UserServiceSync(db)
            existing_user = user_service.get_active_user_by_telegram_id(requester_id)

            if existing_user:
                logger.info("User %s (%s) already has access", requester_id, existing_user.name)

                from src.bot.config import bot_config

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

                await update.message.reply_text(
                    t("requests.already_have_access"), reply_markup=keyboard
                )
                return

            request_service = RequestService(db)
            new_request = await request_service.create_request(
                user_telegram_id=requester_id,
                request_message=request_message,
                user_telegram_username=requester_username,
            )

            if not new_request:
                # T035: Handle duplicate pending request
                logger.warning("Duplicate pending request from requester %s", requester_id)
                await update.message.reply_text(t("requests.duplicate_request"))
                return

            # T029: Send confirmation to requester
            notification_service = NotificationService(context.application)
            await notification_service.send_confirmation_to_requester(requester_id=requester_id)
            logger.info("Sent confirmation to requester %s", requester_id)

            # T030: Send admin notification
            try:
                await notification_service.send_notification_to_admin(
                    request_id=new_request.id,
                    requester_id=requester_id,
                    requester_username=requester_username,
                    request_message=request_message,
                )
                logger.info("Sent admin notification for request %d", new_request.id)
            except Exception as e:
                logger.error("Failed to send admin notification: %s", e)
                # Don't fail the handler if admin notification fails

        finally:
            db.close()

    except Exception as e:
        # T035: Handle and log errors
        logger.error("Error processing /request: %s", e, exc_info=True)
        try:
            await update.message.reply_text(t("errors.error_processing"))
        except Exception as reply_error:
            logger.error("Failed to send error reply: %s", reply_error)


__all__ = ["handle_start_command", "handle_request_command"]
