"""Unit tests for bot initialization."""

from unittest.mock import MagicMock, patch

import pytest

from src.bot import create_bot_app


class TestCreateBotApp:
    """Test cases for bot application creation."""

    @pytest.mark.asyncio
    async def test_create_bot_app_success(self):
        """Test successful bot application creation."""
        with patch("src.bot.Application") as mock_app_class:
            mock_app_builder = MagicMock()
            mock_app_instance = MagicMock()

            mock_app_builder.token.return_value = mock_app_builder
            mock_app_builder.build.return_value = mock_app_instance

            mock_app_class.builder.return_value = mock_app_builder

            with patch("src.bot.bot_config") as mock_config:
                mock_config.telegram_bot_token = "test_token"
                with patch("src.bot.CommandHandler"):
                    with patch("src.bot.MessageHandler"):
                        with patch("src.bot.CallbackQueryHandler"):
                            result = await create_bot_app()

                            assert result is mock_app_instance
                            mock_app_instance.add_handler.assert_called()

    @pytest.mark.asyncio
    async def test_create_bot_app_registers_command_handlers(self):
        """Test bot app registers command handlers correctly."""
        with patch("src.bot.Application") as mock_app_class:
            mock_app_builder = MagicMock()
            mock_app_instance = MagicMock()

            mock_app_builder.token.return_value = mock_app_builder
            mock_app_builder.build.return_value = mock_app_instance

            mock_app_class.builder.return_value = mock_app_builder

            with patch("src.bot.bot_config") as mock_config:
                mock_config.telegram_bot_token = "test_token"
                with patch("src.bot.CommandHandler"):
                    with patch("src.bot.MessageHandler"):
                        with patch("src.bot.CallbackQueryHandler"):
                            with patch("src.bot.handle_request_command"):
                                with patch("src.bot.handle_admin_response"):
                                    with patch("src.bot.handle_admin_callback"):
                                        await create_bot_app()

                                        # Verify add_handler was called multiple times
                                        assert mock_app_instance.add_handler.call_count >= 3

    @pytest.mark.asyncio
    async def test_create_bot_app_registers_message_handler(self):
        """Test bot app registers message handler for admin responses."""
        with patch("src.bot.Application") as mock_app_class:
            mock_app_builder = MagicMock()
            mock_app_instance = MagicMock()

            mock_app_builder.token.return_value = mock_app_builder
            mock_app_builder.build.return_value = mock_app_instance

            mock_app_class.builder.return_value = mock_app_builder

            with patch("src.bot.bot_config") as mock_config:
                mock_config.telegram_bot_token = "test_token"
                with patch("src.bot.CommandHandler"):
                    with patch("src.bot.MessageHandler") as mock_msg_handler_class:
                        with patch("src.bot.CallbackQueryHandler"):
                            with patch("src.bot.handle_admin_response"):
                                with patch("src.bot.handle_admin_callback"):
                                    await create_bot_app()

                                    # Verify MessageHandler was instantiated
                                    mock_msg_handler_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_bot_app_registers_callback_handler(self):
        """Test bot app registers callback query handler for approve/reject buttons."""
        with patch("src.bot.Application") as mock_app_class:
            mock_app_builder = MagicMock()
            mock_app_instance = MagicMock()

            mock_app_builder.token.return_value = mock_app_builder
            mock_app_builder.build.return_value = mock_app_instance

            mock_app_class.builder.return_value = mock_app_builder

            with patch("src.bot.bot_config") as mock_config:
                mock_config.telegram_bot_token = "test_token"
                with patch("src.bot.CommandHandler"):
                    with patch("src.bot.MessageHandler"):
                        with patch("src.bot.CallbackQueryHandler") as mock_callback_class:
                            with patch("src.bot.handle_admin_callback"):
                                await create_bot_app()

                                # Verify CallbackQueryHandler was instantiated
                                mock_callback_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_bot_app_returns_application_instance(self):
        """Test create_bot_app returns an Application instance."""
        with patch("src.bot.Application") as mock_app_class:
            mock_app_builder = MagicMock()
            mock_app_instance = MagicMock()

            mock_app_builder.token.return_value = mock_app_builder
            mock_app_builder.build.return_value = mock_app_instance

            mock_app_class.builder.return_value = mock_app_builder

            with patch("src.bot.bot_config") as mock_config:
                mock_config.telegram_bot_token = "test_token"
                with patch("src.bot.CommandHandler"):
                    with patch("src.bot.MessageHandler"):
                        with patch("src.bot.CallbackQueryHandler"):
                            result = await create_bot_app()

                            assert result == mock_app_instance
