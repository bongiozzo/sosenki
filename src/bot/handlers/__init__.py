"""Bot handlers package - command, requests, and conversation handlers."""

from src.bot.handlers.admin_bills import (
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
    handle_periods_command,
)
from src.bot.handlers.admin_requests import handle_admin_callback, handle_admin_response
from src.bot.handlers.common import handle_request_command, handle_start_command

__all__ = [
    # Common handlers
    "handle_start_command",
    "handle_request_command",
    # Admin: Access requests
    "handle_admin_response",
    "handle_admin_callback",
    # Admin: Period management
    "handle_periods_command",
    "handle_period_action_selection",
    "handle_period_start_date_input",
    "handle_period_end_date_input",
    # Admin: Electricity bills
    "handle_electricity_bills_command",
    "handle_electricity_period_selection",
    "handle_electricity_meter_start",
    "handle_electricity_meter_end",
    "handle_electricity_multiplier",
    "handle_electricity_rate",
    "handle_electricity_losses",
    "handle_electricity_create_bills",
]
