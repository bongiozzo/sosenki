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
from src.bot.handlers.admin_bills import (
    handle_electricity_bills_cancel,
    handle_electricity_bills_command,
    handle_electricity_create_bills,
    handle_electricity_losses,
    handle_electricity_meter_end,
    handle_electricity_meter_start,
    handle_electricity_multiplier,
    handle_electricity_period_selection,
    handle_electricity_rate,
)
from src.bot.handlers.admin_periods import (
    handle_period_action_selection,
    handle_period_end_date_input,
    handle_period_start_date_input,
    handle_periods_cancel,
    handle_periods_command,
)

# Import from handlers package (modular structure)
from src.bot.handlers.admin_requests import handle_admin_callback, handle_admin_response
from src.bot.handlers.common import handle_request_command, handle_start_command

# logger = logging.getLogger(__name__)

# Conversation states for service periods
PERIOD_SELECT_ACTION = 10
PERIOD_INPUT_START_DATE = 11
PERIOD_INPUT_END_DATE = 12

# Conversation states for electricity bills
# States must match return values in admin_bills.py handlers
ELECTRICITY_SELECT_PERIOD = 1
ELECTRICITY_INPUT_ELECTRICITY_START = 2
ELECTRICITY_INPUT_ELECTRICITY_END = 5
ELECTRICITY_INPUT_MULTIPLIER = 6
ELECTRICITY_INPUT_RATE = 7
ELECTRICITY_INPUT_LOSSES = 8
ELECTRICITY_CONFIRM_BILLS = 9


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

    # Handle inline button callbacks (Approve/Reject) - only catch approve/reject patterns
    # This allows other callbacks (like electricity_bills) to pass through to ConversationHandler
    app.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^(approve|reject):"))

    # T050: Register electricity bills management command with ConversationHandler
    electricity_bills_conv = ConversationHandler(
        entry_points=[CommandHandler("bills", handle_electricity_bills_command)],
        states={
            ELECTRICITY_SELECT_PERIOD: [
                CallbackQueryHandler(
                    handle_electricity_period_selection,
                    pattern="^elec_period:",
                )
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
            ELECTRICITY_CONFIRM_BILLS: [
                CallbackQueryHandler(
                    handle_electricity_create_bills,
                    pattern="^elec_bills:",
                )
            ],
        },
        fallbacks=[CommandHandler("bills", handle_electricity_bills_cancel)],
        allow_reentry=True,
    )
    app.add_handler(electricity_bills_conv)

    # Register service periods management command with ConversationHandler
    periods_conv = ConversationHandler(
        entry_points=[CommandHandler("periods", handle_periods_command)],
        states={
            PERIOD_SELECT_ACTION: [
                CallbackQueryHandler(
                    handle_period_action_selection,
                    pattern="^period_action:",
                )
            ],
            PERIOD_INPUT_START_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_period_start_date_input)
            ],
            PERIOD_INPUT_END_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_period_end_date_input)
            ],
        },
        fallbacks=[CommandHandler("periods", handle_periods_cancel)],
        allow_reentry=True,
    )
    app.add_handler(periods_conv)

    # Initialize any other bot-level setup here

    return app


__all__ = ["create_bot_app"]
