"""Electricity bills management handlers with conversation state machine."""

import logging
from decimal import Decimal, InvalidOperation

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
from src.services.electricity_service import ElectricityService
from src.services.localizer import t
from src.utils.parsers import parse_russian_decimal

logger = logging.getLogger(__name__)


# Conversation state constants
class States:
    """Conversation states for electricity bills workflow."""

    END = -1
    SELECT_PERIOD = 1
    INPUT_METER_START = 2
    INPUT_METER_END = 5
    INPUT_MULTIPLIER = 6
    INPUT_RATE = 7
    INPUT_LOSSES = 8
    CONFIRM_BILLS = 9


# Context data keys
_ELECTRICITY_KEYS = [
    "electricity_admin_id",
    "electricity_period_id",
    "electricity_period_name",
    "electricity_start",
    "electricity_end",
    "electricity_multiplier",
    "electricity_rate",
    "electricity_losses",
    "electricity_total_cost",
    "electricity_personal_bills_sum",
    "electricity_shared_cost",
    "electricity_owner_shares",
    "electricity_previous_multiplier",
    "electricity_previous_rate",
    "electricity_previous_losses",
    "authorized_admin",
]


def _clear_electricity_context(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear all electricity-related context data."""
    for key in _ELECTRICITY_KEYS:
        context.user_data.pop(key, None)


def _validate_positive_decimal(text: str, allow_zero: bool = False) -> tuple[Decimal | None, bool]:
    """Validate and parse a positive decimal number.

    Args:
        text: Input text to parse
        allow_zero: If True, zero is valid; if False, must be > 0

    Returns:
        Tuple of (parsed_value, is_valid). If invalid, value is None.
    """
    try:
        value = parse_russian_decimal(text)
        if value is None:
            return None, False
        if allow_zero:
            if value < 0:
                return None, False
        else:
            if value <= 0:
                return None, False
        return value, True
    except (InvalidOperation, ValueError):
        return None, False


def _validate_fraction(text: str) -> tuple[Decimal | None, bool]:
    """Validate and parse a decimal between 0 and 1 (inclusive).

    Args:
        text: Input text to parse

    Returns:
        Tuple of (parsed_value, is_valid). If invalid, value is None.
    """
    try:
        value = parse_russian_decimal(text)
        if value is None or value < 0 or value > 1:
            return None, False
        return value, True
    except (InvalidOperation, ValueError):
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


async def handle_electricity_bills_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancel/reset electricity bills workflow.

    Clears all conversation context and ends the conversation.
    Called when user types /bills while already in active conversation.
    """
    _clear_electricity_context(context)
    return States.END


async def handle_electricity_bills_command(  # noqa: C901
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Start electricity bills management workflow.

    Admin command to interactively calculate and create shared electricity bills.
    Entry point for multi-step conversation.
    Usage: /bills

    T050: Implement electricity bills admin command

    Returns:
        Conversation state for next step (SELECT_PERIOD)
    """
    try:
        if not update.message or not update.message.from_user:
            logger.warning("Received electricity command without message or user")
            return States.END

        telegram_id = update.message.from_user.id

        # Verify admin authorization
        admin_user = await verify_admin_authorization(telegram_id)
        if not admin_user:
            logger.warning("Non-admin attempted electricity command: telegram_id=%d", telegram_id)
            try:
                await update.message.reply_text(t("errors.not_authorized"))
            except Exception:
                pass
            return States.END

        db = SessionLocal()

        try:
            # Query open service periods
            period_service = ServicePeriodService(db)
            open_periods = period_service.get_open_periods(limit=5)

            # Build inline buttons for period selection
            buttons = []
            for period in open_periods[:5]:  # Limit to 5 recent periods
                buttons.append(
                    [
                        InlineKeyboardButton(
                            f"📅 {period.name}", callback_data=f"elec_period:{period.id}"
                        )
                    ]
                )

            keyboard = InlineKeyboardMarkup(buttons)

            await update.message.reply_text(
                t("labels.select_period"),
                reply_markup=keyboard,
            )

            logger.info(
                "Electricity bills workflow started by admin user_id=%d (telegram_id=%d)",
                admin_user.id,
                telegram_id,
            )

            # Store authenticated admin user context
            context.user_data["authorized_admin"] = admin_user
            context.user_data["electricity_admin_id"] = telegram_id

            return States.SELECT_PERIOD

        finally:
            db.close()

    except Exception as e:
        logger.error("Error starting electricity bills workflow: %s", e, exc_info=True)
        try:
            await update.message.reply_text(t("errors.error_processing"))
        except Exception:
            pass
        return States.END


async def handle_electricity_period_selection(  # noqa: C901
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle service period selection for electricity bills.

    User selects existing open service period to fill electricity data.
    """
    try:
        cq = update.callback_query
        if not cq or not cq.data:
            logger.warning("Received period selection callback without data")
            return States.END

        await cq.answer()

        db = SessionLocal()

        try:
            period_service = ServicePeriodService(db)

            # Extract period ID
            try:
                period_id = int(cq.data.split(":")[1])
            except (IndexError, ValueError):
                logger.warning("Invalid period callback data: %s", cq.data)
                await cq.edit_message_text(t("errors.error_processing"))
                return States.END

            # Fetch period
            period = period_service.get_by_id(period_id)
            if not period:
                logger.warning("Period %d not found", period_id)
                await cq.edit_message_text(t("errors.error_processing"))
                return States.END

            # Store selected period
            context.user_data["electricity_period_id"] = period_id
            context.user_data["electricity_period_name"] = period.name

            # Fetch previous period values for defaults
            defaults = period_service.get_previous_period_defaults(period.start_date)

            # Store all previous period values for keyboard buttons
            context.user_data["electricity_previous_rate"] = defaults.electricity_rate
            context.user_data["electricity_previous_multiplier"] = defaults.electricity_multiplier
            context.user_data["electricity_previous_losses"] = defaults.electricity_losses

            # Ask for electricity_start (with default from previous period's electricity_end if available)
            default_start = defaults.electricity_end if defaults.electricity_end else "?"
            prompt = f"{t('labels.meter_start_label')}\n\n({t('labels.previous_value', value=default_start)})"

            # Build reply keyboard with previous period's electricity_end value if available
            keyboard = _build_previous_value_keyboard(defaults.electricity_end)

            # Send prompt with keyboard (if available)
            await cq.message.reply_text(prompt, reply_markup=keyboard)

            return States.INPUT_METER_START

        finally:
            db.close()

    except Exception as e:
        logger.error("Error in period selection: %s", e, exc_info=True)
        try:
            await update.callback_query.edit_message_text(t("errors.error_processing"))
        except Exception:
            logger.debug("Could not edit message after error", exc_info=True)
        return States.END


async def handle_electricity_meter_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle electricity meter start reading input."""
    try:
        if not update.message or not update.message.text:
            return States.INPUT_METER_START

        text = update.message.text.strip()
        value, valid = _validate_positive_decimal(text, allow_zero=True)

        if not valid:
            await update.message.reply_text(t("errors.invalid_number"))
            return States.INPUT_METER_START

        context.user_data["electricity_start"] = value
        await update.message.reply_text(t("labels.meter_end_label"))
        return States.INPUT_METER_END

    except Exception as e:
        logger.error("Error in meter start input: %s", e, exc_info=True)
        try:
            await update.message.reply_text(t("errors.error_processing"))
        except Exception:
            pass
        return States.END


async def handle_electricity_meter_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle electricity meter end reading input."""
    try:
        if not update.message or not update.message.text:
            return States.INPUT_METER_END

        text = update.message.text.strip()
        value, valid = _validate_positive_decimal(text, allow_zero=True)

        if not valid:
            await update.message.reply_text(t("errors.invalid_number"))
            return States.INPUT_METER_END

        electricity_start = context.user_data.get("electricity_start")
        if value <= electricity_start:
            await update.message.reply_text(t("errors.meter_end_less_than_start"))
            return States.INPUT_METER_END

        context.user_data["electricity_end"] = value

        keyboard = _build_previous_value_keyboard(
            context.user_data.get("electricity_previous_multiplier")
        )
        await update.message.reply_text(t("labels.multiplier_label"), reply_markup=keyboard)
        return States.INPUT_MULTIPLIER

    except Exception as e:
        logger.error("Error in meter end input: %s", e, exc_info=True)
        try:
            await update.message.reply_text(t("errors.error_processing"))
        except Exception:
            pass
        return States.END


async def handle_electricity_multiplier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle electricity multiplier input."""
    try:
        if not update.message or not update.message.text:
            return States.INPUT_MULTIPLIER

        text = update.message.text.strip()
        value, valid = _validate_positive_decimal(text)

        if not valid:
            await update.message.reply_text(t("errors.invalid_number"))
            return States.INPUT_MULTIPLIER

        context.user_data["electricity_multiplier"] = value

        keyboard = _build_previous_value_keyboard(
            context.user_data.get("electricity_previous_rate")
        )
        await update.message.reply_text(t("labels.rate_label"), reply_markup=keyboard)
        return States.INPUT_RATE

    except Exception as e:
        logger.error("Error in multiplier input: %s", e, exc_info=True)
        try:
            await update.message.reply_text(t("errors.error_processing"))
        except Exception:
            pass
        return States.END


async def handle_electricity_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle electricity rate input."""
    try:
        if not update.message or not update.message.text:
            return States.INPUT_RATE

        text = update.message.text.strip()
        value, valid = _validate_positive_decimal(text)

        if not valid:
            await update.message.reply_text(t("errors.invalid_number"))
            return States.INPUT_RATE

        context.user_data["electricity_rate"] = value

        keyboard = _build_previous_value_keyboard(
            context.user_data.get("electricity_previous_losses")
        )
        await update.message.reply_text(t("labels.losses_label"), reply_markup=keyboard)
        return States.INPUT_LOSSES

    except Exception as e:
        logger.error("Error in rate input: %s", e, exc_info=True)
        try:
            await update.message.reply_text(t("errors.error_processing"))
        except Exception:
            pass
        return States.END


async def handle_electricity_losses(  # noqa: C901
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle electricity losses input and calculate total cost."""
    try:
        if not update.message or not update.message.text:
            return States.INPUT_LOSSES

        text = update.message.text.strip()
        value, valid = _validate_fraction(text)

        if not valid:
            await update.message.reply_text(t("errors.invalid_losses"))
            return States.INPUT_LOSSES

        context.user_data["electricity_losses"] = value

        # Calculate total electricity cost
        db = SessionLocal()
        try:
            electricity_service = ElectricityService(db)
            period_service = ServicePeriodService(db)

            start = context.user_data.get("electricity_start")
            end = context.user_data.get("electricity_end")
            multiplier = context.user_data.get("electricity_multiplier")
            rate = context.user_data.get("electricity_rate")

            total_cost = electricity_service.calculate_total_electricity(
                start, end, multiplier, rate, value
            )

            context.user_data["electricity_total_cost"] = total_cost

            # Proceed directly to distribute costs among owners (skip confirmation step)
            period_id = context.user_data.get("electricity_period_id")

            # Get existing electricity bills sum
            personal_bills_sum = electricity_service.get_electricity_bills_for_period(period_id)

            # Calculate shared cost
            shared_cost = total_cost - personal_bills_sum

            context.user_data["electricity_personal_bills_sum"] = personal_bills_sum
            context.user_data["electricity_shared_cost"] = shared_cost

            # Fetch the service period
            period = period_service.get_by_id(period_id)
            if not period:
                await update.message.reply_text(t("errors.error_processing"))
                return States.END

            # Distribute costs
            owner_shares = electricity_service.distribute_shared_costs(shared_cost, period)

            context.user_data["electricity_owner_shares"] = owner_shares
            context.user_data["electricity_shared_cost"] = shared_cost

            # Show the proposed bills table with owner shares and summary (skip state 9)
            return await _show_electricity_bills_table(update, context)

        finally:
            db.close()

    except Exception as e:
        logger.error("Error in losses input: %s", e, exc_info=True)
        try:
            await update.message.reply_text(t("errors.error_processing"))
        except Exception:
            pass
        return States.END


async def _show_electricity_bills_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display proposed electricity bills table with percentages and ask for confirmation."""
    try:
        owner_shares = context.user_data.get("electricity_owner_shares", [])

        # Build bills table with percentages and Russian thousand separator formatting
        bills_text = ""
        total_share_weight = Decimal("0")
        total_bill_amount = Decimal("0")

        # First pass: calculate totals
        for share in owner_shares:
            total_share_weight += share.total_share_weight
            total_bill_amount += share.calculated_bill_amount

        # Second pass: build formatted table with percentages
        for share in owner_shares:
            # Calculate percentage
            if total_share_weight > 0:
                percentage = (share.total_share_weight / total_share_weight) * 100
            else:
                percentage = 0

            # Format amounts with Russian thousand separators (space-separated)
            amount_formatted = f"{share.calculated_bill_amount:,.2f}".replace(",", " ")
            bills_text += f"• {share.user_name}: {percentage:.2f}% → {amount_formatted} ₽\n"

        # Add summary line with calculated total percentage
        total_amount_formatted = f"{total_bill_amount:,.2f}".replace(",", " ")
        total_percentage = (
            (total_share_weight / total_share_weight * 100) if total_share_weight > 0 else 0
        )
        bills_text += f"\n*{total_percentage:.2f}% → {total_amount_formatted} ₽*"

        message = t("electricity.confirm_bills_message", bills_table=bills_text)

        buttons = [
            [
                InlineKeyboardButton(t("buttons.create_bills"), callback_data="elec_bills:create"),
                InlineKeyboardButton(t("buttons.cancel"), callback_data="elec_bills:cancel"),
            ]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                message, reply_markup=keyboard, parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(message, reply_markup=keyboard, parse_mode="Markdown")

        return States.CONFIRM_BILLS

    except Exception as e:
        logger.error("Error showing bills table: %s", e, exc_info=True)
        return States.END


async def handle_electricity_create_bills(  # noqa: C901
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Create shared electricity bills in the database."""
    try:
        cq = update.callback_query
        if not cq or not cq.data:
            return States.CONFIRM_BILLS

        await cq.answer()

        if cq.data == "elec_bills:cancel":
            await cq.edit_message_text(t("electricity.operation_cancelled"))
            return States.END

        if cq.data != "elec_bills:create":
            logger.warning("Unexpected callback data: %s", cq.data)
            return States.CONFIRM_BILLS

        # Create bills
        db = SessionLocal()
        try:
            period_service = ServicePeriodService(db)
            owner_shares = context.user_data.get("electricity_owner_shares", [])
            period_id = context.user_data.get("electricity_period_id")

            if not owner_shares or not period_id:
                await cq.edit_message_text(t("errors.error_processing"))
                return States.END

            # Update service period with electricity values and close it
            period_service.update_electricity_data(
                period_id=period_id,
                electricity_start=context.user_data.get("electricity_start"),
                electricity_end=context.user_data.get("electricity_end"),
                electricity_multiplier=context.user_data.get("electricity_multiplier"),
                electricity_rate=context.user_data.get("electricity_rate"),
                electricity_losses=context.user_data.get("electricity_losses"),
                close_period=True,
            )

            # Create bills for each owner
            bills_created = period_service.create_shared_electricity_bills(
                period_id=period_id,
                owner_shares=owner_shares,
            )

            # Confirm success with period name (send as reply to preserve message history)
            period_name = context.user_data.get("electricity_period_name", "период")
            message = t(
                "electricity.bills_created_and_closed", count=bills_created, period_name=period_name
            )
            await cq.message.reply_text(message)

            logger.info(
                "Created %d shared electricity bills for period %d", bills_created, period_id
            )

            return States.END

        except Exception as e:
            db.rollback()
            logger.error("Error creating bills: %s", e, exc_info=True)
            try:
                await cq.edit_message_text(t("errors.error_processing"))
            except Exception:
                pass
            return States.END

        finally:
            db.close()

    except Exception as e:
        logger.error("Error in create bills handler: %s", e, exc_info=True)
        try:
            await update.callback_query.edit_message_text(t("errors.error_processing"))
        except Exception:
            pass
        return States.END


__all__ = [
    "States",
    "handle_electricity_bills_command",
    "handle_electricity_bills_cancel",
    "handle_electricity_period_selection",
    "handle_electricity_meter_start",
    "handle_electricity_meter_end",
    "handle_electricity_multiplier",
    "handle_electricity_rate",
    "handle_electricity_losses",
    "handle_electricity_create_bills",
]
