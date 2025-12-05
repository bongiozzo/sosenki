"""Unit tests for admin_periods.py handler functions."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import CallbackQuery, InlineKeyboardMarkup, Message, Update
from telegram import User as TgUser
from telegram.ext import ContextTypes

from src.bot.handlers.admin_periods import (
    handle_period_action_selection,
    handle_period_end_date_input,
    handle_period_start_date_input,
    handle_periods_cancel,
    handle_periods_command,
)
from src.models.service_period import ServicePeriod
from src.models.user import User


@pytest.fixture
def mock_update():
    """Create a mock Update object for testing."""
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.from_user = MagicMock(spec=TgUser)
    update.message.from_user.id = 123456789
    update.message.reply_text = AsyncMock()
    update.callback_query = None
    return update


@pytest.fixture
def mock_context():
    """Create a mock Context object for testing."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    return context


@pytest.fixture
def mock_admin_user():
    """Create a mock admin User object."""
    user = MagicMock(spec=User)
    user.id = 1
    user.telegram_id = 123456789
    user.is_administrator = True
    user.is_active = True
    return user


# Tests for handle_periods_cancel


@pytest.mark.asyncio
async def test_handle_periods_cancel_clears_context(mock_update, mock_context):
    """Test cancel clears all periods-related context."""
    mock_context.user_data["periods_admin_id"] = 123
    mock_context.user_data["period_start_date"] = date(2025, 1, 1)
    mock_context.user_data["period_end_date"] = date(2025, 1, 31)
    mock_context.user_data["period_id"] = 1
    mock_context.user_data["period_name"] = "Test Period"
    mock_context.user_data["other_data"] = "preserved"

    result = await handle_periods_cancel(mock_update, mock_context)

    assert result == -1
    assert "periods_admin_id" not in mock_context.user_data
    assert "period_start_date" not in mock_context.user_data
    assert "period_end_date" not in mock_context.user_data
    assert "period_id" not in mock_context.user_data
    assert "period_name" not in mock_context.user_data
    assert mock_context.user_data["other_data"] == "preserved"


@pytest.mark.asyncio
async def test_handle_periods_cancel_handles_empty_context(mock_update, mock_context):
    """Test cancel works with no existing period data."""
    result = await handle_periods_cancel(mock_update, mock_context)
    assert result == -1


# Tests for handle_periods_command


@pytest.mark.asyncio
async def test_handle_periods_command_no_message(mock_update, mock_context):
    """Test command returns -1 when no message."""
    mock_update.message = None
    result = await handle_periods_command(mock_update, mock_context)
    assert result == -1


@pytest.mark.asyncio
async def test_handle_periods_command_no_from_user(mock_update, mock_context):
    """Test command returns -1 when no from_user."""
    mock_update.message.from_user = None
    result = await handle_periods_command(mock_update, mock_context)
    assert result == -1


@pytest.mark.asyncio
async def test_handle_periods_command_unauthorized(mock_update, mock_context):
    """Test command rejects unauthorized user."""
    with patch(
        "src.bot.handlers.admin_periods.verify_admin_authorization",
        new=AsyncMock(return_value=None),
    ):
        result = await handle_periods_command(mock_update, mock_context)

    assert result == -1
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_periods_command_authorized(mock_update, mock_context, mock_admin_user):
    """Test command shows action menu for authorized admin."""
    with patch(
        "src.bot.handlers.admin_periods.verify_admin_authorization",
        new=AsyncMock(return_value=mock_admin_user),
    ):
        result = await handle_periods_command(mock_update, mock_context)

    assert result == 10
    assert mock_context.user_data["authorized_admin"] == mock_admin_user
    assert mock_context.user_data["periods_admin_id"] == 123456789
    mock_update.message.reply_text.assert_called_once()
    call_kwargs = mock_update.message.reply_text.call_args
    assert isinstance(call_kwargs.kwargs.get("reply_markup"), InlineKeyboardMarkup)


@pytest.mark.asyncio
async def test_handle_periods_command_exception(mock_update, mock_context):
    """Test command handles exceptions gracefully."""
    with patch(
        "src.bot.handlers.admin_periods.verify_admin_authorization",
        side_effect=Exception("Database error"),
    ):
        result = await handle_periods_command(mock_update, mock_context)

    assert result == -1
    mock_update.message.reply_text.assert_called()


# Tests for handle_period_action_selection


@pytest.fixture
def mock_callback_update():
    """Create a mock Update with callback_query."""
    update = MagicMock(spec=Update)
    update.message = None
    update.callback_query = MagicMock(spec=CallbackQuery)
    update.callback_query.answer = AsyncMock()
    update.callback_query.data = "period_action:create"
    update.callback_query.message = MagicMock(spec=Message)
    update.callback_query.message.reply_text = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


@pytest.mark.asyncio
async def test_handle_period_action_selection_no_callback(mock_update, mock_context):
    """Test action selection returns -1 when no callback query."""
    mock_update.callback_query = None
    result = await handle_period_action_selection(mock_update, mock_context)
    assert result == -1


@pytest.mark.asyncio
async def test_handle_period_action_selection_no_data(mock_callback_update, mock_context):
    """Test action selection returns -1 when no callback data."""
    mock_callback_update.callback_query.data = None
    result = await handle_period_action_selection(mock_callback_update, mock_context)
    assert result == -1


@pytest.mark.asyncio
async def test_handle_period_action_selection_create_no_previous(
    mock_callback_update, mock_context
):
    """Test create action without previous period."""
    mock_callback_update.callback_query.data = "period_action:create"

    mock_service = MagicMock()
    mock_service.get_latest_period.return_value = None

    with patch("src.bot.handlers.admin_periods.SessionLocal") as mock_db:
        mock_session = MagicMock()
        mock_db.return_value = mock_session
        with patch(
            "src.bot.handlers.admin_periods.ServicePeriodService",
            return_value=mock_service,
        ):
            result = await handle_period_action_selection(mock_callback_update, mock_context)

    assert result == 11
    mock_callback_update.callback_query.answer.assert_called_once()
    mock_callback_update.callback_query.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_period_action_selection_create_with_previous(
    mock_callback_update, mock_context
):
    """Test create action with previous period suggests date."""
    mock_callback_update.callback_query.data = "period_action:create"

    mock_period = MagicMock(spec=ServicePeriod)
    mock_period.end_date = date(2025, 1, 31)

    mock_service = MagicMock()
    mock_service.get_latest_period.return_value = mock_period

    with patch("src.bot.handlers.admin_periods.SessionLocal") as mock_db:
        mock_session = MagicMock()
        mock_db.return_value = mock_session
        with patch(
            "src.bot.handlers.admin_periods.ServicePeriodService",
            return_value=mock_service,
        ):
            result = await handle_period_action_selection(mock_callback_update, mock_context)

    assert result == 11


@pytest.mark.asyncio
async def test_handle_period_action_selection_view_empty(mock_callback_update, mock_context):
    """Test view action with no periods."""
    mock_callback_update.callback_query.data = "period_action:view"

    mock_service = MagicMock()
    mock_service.list_periods.return_value = []

    with patch("src.bot.handlers.admin_periods.SessionLocal") as mock_db:
        mock_session = MagicMock()
        mock_db.return_value = mock_session
        with patch(
            "src.bot.handlers.admin_periods.ServicePeriodService",
            return_value=mock_service,
        ):
            result = await handle_period_action_selection(mock_callback_update, mock_context)

    assert result == -1
    mock_callback_update.callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_period_action_selection_view_with_periods(mock_callback_update, mock_context):
    """Test view action with existing periods."""
    mock_callback_update.callback_query.data = "period_action:view"

    mock_period_open = MagicMock(spec=ServicePeriod)
    mock_period_open.name = "Test Period 1"
    mock_period_open.status = "open"

    mock_period_closed = MagicMock(spec=ServicePeriod)
    mock_period_closed.name = "Test Period 2"
    mock_period_closed.status = "closed"

    mock_service = MagicMock()
    mock_service.list_periods.return_value = [mock_period_open, mock_period_closed]

    with patch("src.bot.handlers.admin_periods.SessionLocal") as mock_db:
        mock_session = MagicMock()
        mock_db.return_value = mock_session
        with patch(
            "src.bot.handlers.admin_periods.ServicePeriodService",
            return_value=mock_service,
        ):
            result = await handle_period_action_selection(mock_callback_update, mock_context)

    assert result == -1


@pytest.mark.asyncio
async def test_handle_period_action_selection_unknown_action(mock_callback_update, mock_context):
    """Test unknown action returns -1."""
    mock_callback_update.callback_query.data = "period_action:unknown"

    result = await handle_period_action_selection(mock_callback_update, mock_context)

    assert result == -1
    mock_callback_update.callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_period_action_selection_exception(mock_callback_update, mock_context):
    """Test action selection handles exceptions."""
    mock_callback_update.callback_query.data = "period_action:create"
    mock_callback_update.callback_query.answer = AsyncMock(side_effect=Exception("Error"))
    mock_callback_update.callback_query.edit_message_text = AsyncMock()

    result = await handle_period_action_selection(mock_callback_update, mock_context)

    assert result == -1


# Tests for handle_period_start_date_input


@pytest.mark.asyncio
async def test_handle_period_start_date_input_no_message(mock_update, mock_context):
    """Test start date input returns 11 when no message."""
    mock_update.message = None
    result = await handle_period_start_date_input(mock_update, mock_context)
    assert result == 11


@pytest.mark.asyncio
async def test_handle_period_start_date_input_no_text(mock_update, mock_context):
    """Test start date input returns 11 when no text."""
    mock_update.message.text = None
    result = await handle_period_start_date_input(mock_update, mock_context)
    assert result == 11


@pytest.mark.asyncio
async def test_handle_period_start_date_input_invalid_format(mock_update, mock_context):
    """Test start date input rejects invalid format."""
    mock_update.message.text = "2025-01-01"  # Wrong format
    result = await handle_period_start_date_input(mock_update, mock_context)
    assert result == 11
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_period_start_date_input_valid(mock_update, mock_context):
    """Test start date input accepts valid format."""
    mock_update.message.text = "01.01.2025"
    result = await handle_period_start_date_input(mock_update, mock_context)
    assert result == 12
    assert mock_context.user_data["period_start_date"] == date(2025, 1, 1)
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_period_start_date_input_exception(mock_update, mock_context):
    """Test start date input handles exceptions."""
    mock_update.message.text = "01.01.2025"
    mock_update.message.reply_text = AsyncMock(side_effect=Exception("Error"))

    result = await handle_period_start_date_input(mock_update, mock_context)
    assert result == -1


# Tests for handle_period_end_date_input


@pytest.mark.asyncio
async def test_handle_period_end_date_input_no_message(mock_update, mock_context):
    """Test end date input returns 12 when no message."""
    mock_update.message = None
    result = await handle_period_end_date_input(mock_update, mock_context)
    assert result == 12


@pytest.mark.asyncio
async def test_handle_period_end_date_input_no_text(mock_update, mock_context):
    """Test end date input returns 12 when no text."""
    mock_update.message.text = None
    result = await handle_period_end_date_input(mock_update, mock_context)
    assert result == 12


@pytest.mark.asyncio
async def test_handle_period_end_date_input_invalid_format(mock_update, mock_context):
    """Test end date input rejects invalid format."""
    mock_context.user_data["period_start_date"] = date(2025, 1, 1)
    mock_update.message.text = "invalid"
    result = await handle_period_end_date_input(mock_update, mock_context)
    assert result == 12
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_period_end_date_input_before_start(mock_update, mock_context):
    """Test end date input rejects date before start."""
    mock_context.user_data["period_start_date"] = date(2025, 1, 15)
    mock_update.message.text = "01.01.2025"
    result = await handle_period_end_date_input(mock_update, mock_context)
    assert result == 12


@pytest.mark.asyncio
async def test_handle_period_end_date_input_equal_to_start(mock_update, mock_context):
    """Test end date input rejects date equal to start."""
    mock_context.user_data["period_start_date"] = date(2025, 1, 1)
    mock_update.message.text = "01.01.2025"
    result = await handle_period_end_date_input(mock_update, mock_context)
    assert result == 12


@pytest.mark.asyncio
async def test_handle_period_end_date_input_valid_creates_period(mock_update, mock_context):
    """Test end date input creates period on valid date."""
    mock_context.user_data["period_start_date"] = date(2025, 1, 1)
    mock_context.user_data["periods_admin_id"] = 123
    mock_update.message.text = "31.01.2025"

    mock_period = MagicMock(spec=ServicePeriod)
    mock_period.id = 1
    mock_period.name = "01.01.2025 - 31.01.2025"

    mock_service = MagicMock()
    mock_service.create_period.return_value = mock_period

    with patch("src.bot.handlers.admin_periods.SessionLocal") as mock_db:
        mock_session = MagicMock()
        mock_db.return_value = mock_session
        with patch(
            "src.bot.handlers.admin_periods.ServicePeriodService",
            return_value=mock_service,
        ):
            result = await handle_period_end_date_input(mock_update, mock_context)

    assert result == -1
    assert mock_context.user_data["period_id"] == 1
    assert mock_context.user_data["period_name"] == "01.01.2025 - 31.01.2025"
    mock_service.create_period.assert_called_once_with(date(2025, 1, 1), date(2025, 1, 31), actor_id=123)


@pytest.mark.asyncio
async def test_handle_period_end_date_input_exception(mock_update, mock_context):
    """Test end date input handles exceptions."""
    mock_context.user_data["period_start_date"] = date(2025, 1, 1)
    mock_update.message.text = "31.01.2025"

    with patch("src.bot.handlers.admin_periods.SessionLocal") as mock_db:
        mock_db.side_effect = Exception("Database error")
        result = await handle_period_end_date_input(mock_update, mock_context)

    assert result == -1
