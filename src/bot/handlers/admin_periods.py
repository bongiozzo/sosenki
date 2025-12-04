"""Service period management handlers with conversation state machine."""

import logging
from datetime import date

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import ContextTypes

from src.bot.auth import verify_admin_authorization
from src.services import ServicePeriodService, SessionLocal
from src.services.localizer import t
from src.utils.parsers import parse_date

logger = logging.getLogger(__name__)


# Conversation state constants
class States:
    """Conversation states for service periods workflow."""

    END = -1
    SELECT_ACTION = 10
    INPUT_START_DATE = 11
    INPUT_END_DATE = 12


# Context data keys
_PERIODS_KEYS = [
    "periods_admin_id",
    "period_start_date",
    "period_end_date",
    "period_id",
    "period_name",
    "authorized_admin",
]


def _clear_periods_context(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear all periods-related context data."""
    for key in _PERIODS_KEYS:
        context.user_data.pop(key, None)


def _validate_date(text: str) -> tuple[date | None, bool]:
    """Validate and parse a date in DD.MM.YYYY format.

    Args:
        text: Input text to parse

    Returns:
        Tuple of (parsed_date, is_valid). If invalid, date is None.
    """
    try:
        value = parse_date(text)
        if value is None:
            return None, False
        return value, True
    except ValueError:
        return None, False


def _build_previous_value_keyboard(previous_value: str | None) -> ReplyKeyboardMarkup | None:
    """Build a keyboard with a previous value button if available."""
    if not previous_value:
        return None
    return ReplyKeyboardMarkup(
        [[KeyboardButton(text=previous_value)]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )


async def handle_periods_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel/reset service periods workflow.

    Clears all conversation context and ends the conversation.
    Called when user types /periods while already in active conversation.
    """
    _clear_periods_context(context)
    return States.END


async def handle_periods_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start service periods management workflow.

    Admin command to create and manage service periods.
    Entry point for period management conversation.

    Returns:
        Conversation state for next step (SELECT_ACTION)
    """
    try:
        if not update.message or not update.message.from_user:
            logger.warning("Received periods command without message or user")
            return States.END

        telegram_id = update.message.from_user.id

        # Verify admin authorization
        admin_user = await verify_admin_authorization(telegram_id)
        if not admin_user:
            logger.warning("Non-admin attempted periods command: telegram_id=%d", telegram_id)
            try:
                await update.message.reply_text(t("errors.not_authorized"))
            except Exception:
                pass
            return States.END

        # Store authenticated admin user context
        context.user_data["authorized_admin"] = admin_user
        context.user_data["periods_admin_id"] = telegram_id

        # Show action menu
        buttons = [
            [InlineKeyboardButton(t("labels.new_period"), callback_data="period_action:create")],
            [InlineKeyboardButton(t("labels.view_periods"), callback_data="period_action:view")],
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        await update.message.reply_text(
            t("labels.select_action"),
            reply_markup=keyboard,
        )

        logger.info(
            "Service periods workflow started by admin user_id=%d (telegram_id=%d)",
            admin_user.id,
            telegram_id,
        )

        return States.SELECT_ACTION

    except Exception as e:
        logger.error("Error starting periods workflow: %s", e, exc_info=True)
        try:
            await update.message.reply_text(t("errors.error_processing"))
        except Exception:
            pass
        return States.END


async def handle_period_action_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle period action selection: create new period or view existing periods."""
    try:
        cq = update.callback_query
        if not cq or not cq.data:
            logger.warning("Received period action callback without data")
            return States.END

        await cq.answer()

        if cq.data == "period_action:create":
            # Start new period creation flow
            # Query max end_date from existing periods to suggest as default start date
            db = SessionLocal()
            try:
                period_service = ServicePeriodService(db)
                last_period = period_service.get_latest_period()

                keyboard = None
                if last_period and last_period.end_date:
                    suggested_start_str = last_period.end_date.strftime("%d.%m.%Y")
                    keyboard = _build_previous_value_keyboard(suggested_start_str)

                await cq.message.reply_text(
                    t("labels.period_start_date_prompt"), reply_markup=keyboard
                )
                return States.INPUT_START_DATE

            finally:
                db.close()

        elif cq.data == "period_action:view":
            # Show existing periods
            db = SessionLocal()
            try:
                period_service = ServicePeriodService(db)
                periods = period_service.list_periods(limit=10)

                if not periods:
                    await cq.edit_message_text(t("labels.no_periods_found"))
                    return States.END

                periods_text = t("labels.existing_periods_title") + "\n\n"
                for period in periods:
                    status_emoji = "🟢" if period.status == "open" else "🔴"
                    status_text = (
                        t("status.period_open")
                        if period.status == "open"
                        else t("status.period_closed")
                    )
                    periods_text += (
                        f"{status_emoji} {period.name}\n"
                        f"   {t('labels.status_label')} {status_text}\n\n"
                    )

                await cq.edit_message_text(periods_text, parse_mode="Markdown")
                return States.END

            finally:
                db.close()

        else:
            logger.warning("Unknown period action: %s", cq.data)
            await cq.edit_message_text(t("errors.error_processing"))
            return States.END

    except Exception as e:
        logger.error("Error in period action selection: %s", e, exc_info=True)
        try:
            await update.callback_query.edit_message_text(t("errors.error_processing"))
        except Exception:
            logger.debug("Could not edit message after error", exc_info=True)
        return States.END


async def handle_period_start_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle start date input for new service period.

    Validates date format (DD.MM.YYYY).
    """
    try:
        if not update.message or not update.message.text:
            return States.INPUT_START_DATE

        text = update.message.text.strip()
        value, valid = _validate_date(text)

        if not valid:
            await update.message.reply_text(t("errors.invalid_date_format"))
            return States.INPUT_START_DATE

        context.user_data["period_start_date"] = value

        await update.message.reply_text(t("labels.period_end_date_prompt"))
        return States.INPUT_END_DATE

    except Exception as e:
        logger.error("Error in period start date input: %s", e, exc_info=True)
        try:
            await update.message.reply_text(t("errors.error_processing"))
        except Exception:
            pass
        return States.END


async def handle_period_end_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle end date input for new service period.

    Validates that end_date > start_date and creates ServicePeriod in database.
    Status is set to "open" by design.
    """
    try:
        if not update.message or not update.message.text:
            return States.INPUT_END_DATE

        text = update.message.text.strip()
        value, valid = _validate_date(text)

        if not valid:
            await update.message.reply_text(t("errors.invalid_date_format"))
            return States.INPUT_END_DATE

        start_date = context.user_data.get("period_start_date")
        if value <= start_date:
            await update.message.reply_text(t("errors.end_date_before_start"))
            return States.INPUT_END_DATE

        context.user_data["period_end_date"] = value

        # Create ServicePeriod via service
        db = SessionLocal()
        try:
            period_service = ServicePeriodService(db)
            new_period = period_service.create_period(start_date, value)

            context.user_data["period_id"] = new_period.id
            context.user_data["period_name"] = new_period.name

            logger.info(
                "Created new service period: id=%d, name=%s, dates=%s to %s, admin_id=%d",
                new_period.id,
                new_period.name,
                start_date,
                value,
                context.user_data.get("periods_admin_id"),
            )

            # Show confirmation with period details
            status_emoji = "🟢"
            message = (
                f"✅ {t('labels.period_created_success')}\n\n"
                f"{status_emoji} {new_period.name}\n"
                f"   {t('labels.status_label')} {t('status.period_open')}"
            )
            await update.message.reply_text(message)

            return States.END

        finally:
            db.close()

    except Exception as e:
        logger.error("Error in period end date input: %s", e, exc_info=True)
        try:
            await update.message.reply_text(t("errors.error_processing"))
        except Exception:
            pass
        return States.END


__all__ = [
    "States",
    "handle_periods_command",
    "handle_periods_cancel",
    "handle_period_action_selection",
    "handle_period_start_date_input",
    "handle_period_end_date_input",
]
