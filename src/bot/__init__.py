"""Telegram bot application factory."""

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from src.bot.config import bot_config
from src.bot.handlers import (
    handle_admin_callback,
    handle_admin_response,
    handle_request_command,
)

# logger = logging.getLogger(__name__)


async def create_bot_app() -> Application:
    """Create and return Telegram bot application with async handlers.

    T032, T044, T052: Register command handlers with the bot application.
    """
    app = Application.builder().token(bot_config.telegram_bot_token).build()

    # T031/T032: Register /request command handler
    app.add_handler(CommandHandler("request", handle_request_command))
    # Unified admin response handler: handles both Approve and Reject replies
    # Register after /request so it only handles replies to notifications
    # Uses a simple filter: any text message that is a reply (handler will validate content)
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, handle_admin_response))

    # Handle inline button callbacks (Approve/Reject)
    app.add_handler(CallbackQueryHandler(handle_admin_callback))

    # Initialize any other bot-level setup here

    return app


__all__ = ["create_bot_app"]
