"""Unit tests for admin_bills.py handler functions."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from telegram import CallbackQuery, Message, Update
from telegram import User as TgUser
from telegram.ext import ContextTypes

from src.bot.handlers.admin_bills import (
    States,
    handle_electricity_bills_cancel,
    handle_electricity_bills_command,
    handle_electricity_losses,
    handle_electricity_meter_end,
    handle_electricity_meter_start,
    handle_electricity_multiplier,
    handle_electricity_rate,
)
from src.models.user import User


@pytest.fixture
def mock_update():
    """Create mock Update with message."""
    update = AsyncMock(spec=Update)
    update.message = AsyncMock(spec=Message)
    update.message.from_user = AsyncMock(spec=TgUser)
    update.message.from_user.id = 123456789
    update.message.text = ""
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_callback_update():
    """Create mock Update with callback query."""
    update = AsyncMock(spec=Update)
    update.callback_query = AsyncMock(spec=CallbackQuery)
    update.callback_query.data = ""
    update.callback_query.answer = AsyncMock()
    update.callback_query.message = AsyncMock(spec=Message)
    update.callback_query.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock context."""
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    return context


@pytest.fixture
def mock_admin_user():
    """Create mock admin user."""
    user = AsyncMock(spec=User)
    user.id = 1
    user.is_administrator = True
    user.is_active = True
    return user


@pytest.mark.asyncio
async def test_handle_electricity_bills_cancel():
    """Test cancel handler clears context and returns -1."""
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {
        "electricity_admin_id": 123,
        "electricity_period_id": 456,
        "electricity_start": Decimal("100"),
        "electricity_end": Decimal("200"),
        "electricity_multiplier": Decimal("1.0"),
        "electricity_rate": Decimal("5.5"),
        "electricity_losses": Decimal("0.2"),
        "electricity_owner_shares": {"acc1": Decimal("0.5")},
        "electricity_previous_multiplier": "1.0",
        "electricity_previous_rate": "5.5",
        "electricity_previous_losses": "0.2",
    }

    result = await handle_electricity_bills_cancel(None, context)

    assert result == States.END
    assert context.user_data == {}


@pytest.mark.asyncio
async def test_handle_electricity_bills_command_not_authorized(mock_update, mock_context):
    """Test command handler when user is not authorized."""
    with patch("src.bot.handlers.admin_bills.verify_admin_authorization", return_value=None):
        result = await handle_electricity_bills_command(mock_update, mock_context)

    assert result == States.END
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_electricity_bills_command_authorized(
    mock_update, mock_context, mock_admin_user
):
    """Test command handler when user is authorized."""
    with patch(
        "src.bot.handlers.admin_bills.verify_admin_authorization", return_value=mock_admin_user
    ):
        result = await handle_electricity_bills_command(mock_update, mock_context)

    assert result == States.SELECT_PERIOD
    assert mock_context.user_data["authorized_admin"] == mock_admin_user
    assert mock_context.user_data["electricity_admin_id"] == 123456789
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_electricity_bills_command_no_message(mock_context):
    """Test command handler without message."""
    update = AsyncMock(spec=Update)
    update.message = None

    result = await handle_electricity_bills_command(update, mock_context)

    assert result == States.END


@pytest.mark.asyncio
async def test_handle_electricity_meter_start_valid(mock_update, mock_context):
    """Test valid meter start input."""
    mock_update.message.text = "150.50"

    result = await handle_electricity_meter_start(mock_update, mock_context)

    assert result == States.INPUT_METER_END
    assert mock_context.user_data["electricity_start"] == Decimal("150.50")
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_electricity_meter_start_invalid_number(mock_update, mock_context):
    """Test invalid meter start input."""
    mock_update.message.text = "invalid"

    result = await handle_electricity_meter_start(mock_update, mock_context)

    assert result == States.INPUT_METER_START  # Re-ask
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_electricity_meter_start_negative(mock_update, mock_context):
    """Test negative meter start input."""
    mock_update.message.text = "-50"

    result = await handle_electricity_meter_start(mock_update, mock_context)

    assert result == States.INPUT_METER_START  # Re-ask
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_electricity_meter_end_valid(mock_update, mock_context):
    """Test valid meter end input."""
    mock_context.user_data["electricity_start"] = Decimal("100")
    mock_update.message.text = "200.75"

    result = await handle_electricity_meter_end(mock_update, mock_context)

    assert result == States.INPUT_MULTIPLIER
    assert mock_context.user_data["electricity_end"] == Decimal("200.75")
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_electricity_meter_end_less_than_start(mock_update, mock_context):
    """Test meter end less than or equal to start."""
    mock_context.user_data["electricity_start"] = Decimal("200")
    mock_update.message.text = "150"

    result = await handle_electricity_meter_end(mock_update, mock_context)

    assert result == States.INPUT_METER_END  # Re-ask
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_electricity_multiplier_valid(mock_update, mock_context):
    """Test valid multiplier input."""
    mock_update.message.text = "2.5"

    result = await handle_electricity_multiplier(mock_update, mock_context)

    assert result == States.INPUT_RATE
    assert mock_context.user_data["electricity_multiplier"] == Decimal("2.5")
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_electricity_multiplier_zero(mock_update, mock_context):
    """Test zero multiplier input."""
    mock_update.message.text = "0"

    result = await handle_electricity_multiplier(mock_update, mock_context)

    assert result == States.INPUT_MULTIPLIER  # Re-ask
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_electricity_rate_valid(mock_update, mock_context):
    """Test valid rate input."""
    mock_update.message.text = "5.50"

    result = await handle_electricity_rate(mock_update, mock_context)

    assert result == States.INPUT_LOSSES
    assert mock_context.user_data["electricity_rate"] == Decimal("5.50")
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_electricity_rate_invalid(mock_update, mock_context):
    """Test invalid rate input."""
    mock_update.message.text = "abc"

    result = await handle_electricity_rate(mock_update, mock_context)

    assert result == States.INPUT_RATE  # Re-ask
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_electricity_losses_valid(mock_update, mock_context):
    """Test valid losses input."""
    mock_context.user_data["electricity_start"] = Decimal("100")
    mock_context.user_data["electricity_end"] = Decimal("200")
    mock_context.user_data["electricity_multiplier"] = Decimal("1.0")
    mock_context.user_data["electricity_rate"] = Decimal("5.5")
    mock_context.user_data["electricity_period_id"] = 1
    mock_update.message.text = "0.2"

    # Mock the callback query for bills table display
    mock_update.callback_query = AsyncMock()
    mock_update.callback_query.message = AsyncMock()
    mock_update.callback_query.message.edit_text = AsyncMock()

    with patch("src.bot.handlers.admin_bills.SessionLocal"):
        with patch("src.bot.handlers.admin_bills.ElectricityService"):
            with patch("src.bot.handlers.admin_bills.ServicePeriodService") as mock_period_service:
                mock_service_inst = AsyncMock()
                mock_period_service.return_value = mock_service_inst
                mock_service_inst.get_by_id.return_value = None
                mock_service_inst.list_accounts.return_value = []

                result = await handle_electricity_losses(mock_update, mock_context)

    assert result == States.CONFIRM_BILLS
    assert mock_context.user_data["electricity_losses"] == Decimal("0.2")


@pytest.mark.asyncio
async def test_handle_electricity_losses_invalid_range(mock_update, mock_context):
    """Test losses outside valid range."""
    mock_update.message.text = "1.5"

    result = await handle_electricity_losses(mock_update, mock_context)

    assert result == States.INPUT_LOSSES  # Re-ask
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_electricity_losses_negative(mock_update, mock_context):
    """Test negative losses input."""
    mock_update.message.text = "-0.1"

    result = await handle_electricity_losses(mock_update, mock_context)

    assert result == States.INPUT_LOSSES  # Re-ask
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_electricity_meter_start_no_message(mock_update, mock_context):
    """Test meter start handler without message."""
    mock_update.message = None

    result = await handle_electricity_meter_start(mock_update, mock_context)

    assert result == States.INPUT_METER_START


@pytest.mark.asyncio
async def test_handle_electricity_multiplier_with_previous_value(mock_update, mock_context):
    """Test multiplier input shows previous value button."""
    mock_context.user_data["electricity_previous_multiplier"] = "2.0"
    mock_update.message.text = "2.5"

    result = await handle_electricity_multiplier(mock_update, mock_context)

    assert result == States.INPUT_RATE
    call_args = mock_update.message.reply_text.call_args
    assert call_args is not None
    # Verify reply_markup argument has keyboard
    assert "reply_markup" in call_args.kwargs


@pytest.mark.asyncio
async def test_handle_electricity_rate_with_previous_value(mock_update, mock_context):
    """Test rate input shows previous value button."""
    mock_context.user_data["electricity_previous_rate"] = "5.0"
    mock_update.message.text = "5.50"

    result = await handle_electricity_rate(mock_update, mock_context)

    assert result == States.INPUT_LOSSES
    call_args = mock_update.message.reply_text.call_args
    assert call_args is not None
    assert "reply_markup" in call_args.kwargs


@pytest.mark.asyncio
async def test_handle_electricity_meter_start_comma_decimal(mock_update, mock_context):
    """Test meter start with comma as decimal separator."""
    mock_update.message.text = "150,50"

    result = await handle_electricity_meter_start(mock_update, mock_context)

    assert result == States.INPUT_METER_END
    assert mock_context.user_data["electricity_start"] == Decimal("150.50")


@pytest.mark.asyncio
async def test_handle_electricity_multiplier_comma_decimal(mock_update, mock_context):
    """Test multiplier with comma as decimal separator."""
    mock_update.message.text = "2,5"

    result = await handle_electricity_multiplier(mock_update, mock_context)

    assert result == States.INPUT_RATE
    assert mock_context.user_data["electricity_multiplier"] == Decimal("2.5")


@pytest.mark.asyncio
async def test_handle_electricity_rate_comma_decimal(mock_update, mock_context):
    """Test rate with comma as decimal separator."""
    mock_update.message.text = "5,50"

    result = await handle_electricity_rate(mock_update, mock_context)

    assert result == States.INPUT_LOSSES
    assert mock_context.user_data["electricity_rate"] == Decimal("5.50")


@pytest.mark.asyncio
async def test_handle_electricity_losses_comma_decimal(mock_update, mock_context):
    """Test losses with comma as decimal separator."""
    mock_context.user_data["electricity_start"] = Decimal("100")
    mock_context.user_data["electricity_end"] = Decimal("200")
    mock_context.user_data["electricity_multiplier"] = Decimal("1.0")
    mock_context.user_data["electricity_rate"] = Decimal("5.5")
    mock_context.user_data["electricity_period_id"] = 1
    mock_update.message.text = "0,2"

    # Mock callback query for bills table
    mock_update.callback_query = AsyncMock()
    mock_update.callback_query.message = AsyncMock()
    mock_update.callback_query.message.edit_text = AsyncMock()

    with patch("src.bot.handlers.admin_bills.SessionLocal"):
        with patch("src.bot.handlers.admin_bills.ElectricityService"):
            with patch("src.bot.handlers.admin_bills.ServicePeriodService"):
                result = await handle_electricity_losses(mock_update, mock_context)

    assert result == States.CONFIRM_BILLS
    assert mock_context.user_data["electricity_losses"] == Decimal("0.2")
