"""Telegram bot application factory."""

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.bot.config import bot_config
from src.bot.handlers import (
    handle_admin_callback,
    handle_admin_response,
    handle_electricity_bills_command,
    handle_electricity_confirm_calculation,
    handle_electricity_create_bills,
    handle_electricity_end_date_input,
    handle_electricity_losses,
    handle_electricity_meter_end,
    handle_electricity_meter_start,
    handle_electricity_multiplier,
    handle_electricity_period_selection,
    handle_electricity_rate,
    handle_electricity_start_date_input,
    handle_request_command,
    handle_start_command,
)

# logger = logging.getLogger(__name__)

# Conversation states for electricity bills
ELECTRICITY_SELECT_PERIOD = 1
ELECTRICITY_INPUT_START_DATE = 2
ELECTRICITY_INPUT_ELECTRICITY_START = 3
ELECTRICITY_INPUT_END_DATE = 4
ELECTRICITY_INPUT_ELECTRICITY_END = 5
ELECTRICITY_INPUT_MULTIPLIER = 6
ELECTRICITY_INPUT_RATE = 7
ELECTRICITY_INPUT_LOSSES = 8
ELECTRICITY_CONFIRM_CALCULATION = 9
ELECTRICITY_CONFIRM_BILLS = 10


async def create_bot_app() -> Application:
    """Create and return Telegram bot application with async handlers.

    T032, T044, T052: Register command handlers with the bot application.
    """
    app = Application.builder().token(bot_config.telegram_bot_token).build()

    # /start command handler
    app.add_handler(CommandHandler("start", handle_start_command))
    # T031/T032: Register /request command handler
    app.add_handler(CommandHandler("request", handle_request_command))
    # Unified admin response handler: handles both Approve and Reject replies
    # Register after /request so it only handles replies to notifications
    # Uses a simple filter: any text message that is a reply (handler will validate content)
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, handle_admin_response))

    # Handle inline button callbacks (Approve/Reject)
    app.add_handler(CallbackQueryHandler(handle_admin_callback))

    # T050: Register electricity bills management command with ConversationHandler
    electricity_bills_conv = ConversationHandler(
        entry_points=[CommandHandler("electricity_bills", handle_electricity_bills_command)],
        states={
            ELECTRICITY_SELECT_PERIOD: [
                CallbackQueryHandler(
                    handle_electricity_period_selection,
                    pattern="^elec_period:",
                )
            ],
            ELECTRICITY_INPUT_START_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_electricity_start_date_input)
            ],
            ELECTRICITY_INPUT_END_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_electricity_end_date_input)
            ],
            ELECTRICITY_INPUT_ELECTRICITY_START: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_electricity_meter_start)
            ],
            ELECTRICITY_INPUT_ELECTRICITY_END: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_electricity_meter_end)
            ],
            ELECTRICITY_INPUT_MULTIPLIER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_electricity_multiplier)
            ],
            ELECTRICITY_INPUT_RATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_electricity_rate)
            ],
            ELECTRICITY_INPUT_LOSSES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_electricity_losses)
            ],
            ELECTRICITY_CONFIRM_CALCULATION: [
                CallbackQueryHandler(
                    handle_electricity_confirm_calculation,
                    pattern="^elec_confirm:",
                )
            ],
            ELECTRICITY_CONFIRM_BILLS: [
                CallbackQueryHandler(
                    handle_electricity_create_bills,
                    pattern="^elec_bills:",
                )
            ],
        },
        fallbacks=[],
    )
    app.add_handler(electricity_bills_conv)

    # Initialize any other bot-level setup here

    return app


__all__ = ["create_bot_app"]
