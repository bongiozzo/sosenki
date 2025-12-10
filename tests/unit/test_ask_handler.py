"""Unit tests for /ask command handler."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


class TestAskHandler:
    """Tests for the /ask command handler."""

    @pytest.mark.asyncio
    async def test_handle_ask_no_message(self):
        """Test handler ignores updates without message."""
        from src.bot.handlers.ask import handle_ask_command

        update = MagicMock()
        update.message = None
        context = MagicMock()

        result = await handle_ask_command(update, context)

        assert result is None

    @pytest.mark.asyncio
    async def test_handle_ask_no_text(self):
        """Test handler ignores messages without text."""
        from src.bot.handlers.ask import handle_ask_command

        update = MagicMock()
        update.message = MagicMock()
        update.message.text = None
        context = MagicMock()

        result = await handle_ask_command(update, context)

        assert result is None

    @pytest.mark.asyncio
    async def test_handle_ask_empty_question(self):
        """Test handler sends usage message for empty question."""
        from src.bot.handlers.ask import handle_ask_command

        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "/ask"
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        with patch("src.bot.handlers.ask.is_llm_enabled", return_value=True):
            await handle_ask_command(update, context)

            update.message.reply_text.assert_called_once()
            call_args = update.message.reply_text.call_args[0][0]
            assert "Please provide a question" in call_args

    @pytest.mark.asyncio
    async def test_handle_ask_unauthenticated_user(self):
        """Test handler rejects unauthenticated users."""
        from src.bot.handlers.ask import handle_ask_command

        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "/ask What is my balance?"
        update.message.from_user = MagicMock()
        update.message.from_user.id = 12345
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        with patch("src.bot.handlers.ask.is_llm_enabled", return_value=True):
            with patch("src.bot.handlers.ask.AsyncSessionLocal") as mock_session_cls:
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_cls.return_value = mock_session

                with patch("src.services.auth_service.get_authenticated_user") as mock_auth:
                    mock_auth.side_effect = HTTPException(status_code=401, detail="Not authorized")

                    await handle_ask_command(update, context)

                    # Handler uses t("errors.not_authorized") which returns localized message
                update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_ask_success(self):
        """Test handler successfully processes question."""
        from src.bot.handlers.ask import handle_ask_command

        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "/ask What is my balance?"
        update.message.from_user = MagicMock()
        update.message.from_user.id = 12345
        update.message.reply_text = AsyncMock()
        update.message.chat = MagicMock()
        update.message.chat.send_action = AsyncMock()
        context = MagicMock()

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_administrator = False

        with patch("src.bot.handlers.ask.is_llm_enabled", return_value=True):
            with patch("src.bot.handlers.ask.AsyncSessionLocal") as mock_session_cls:
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_cls.return_value = mock_session

                with patch("src.services.auth_service.get_authenticated_user") as mock_auth:
                    mock_auth.return_value = mock_user

                    with patch("src.bot.handlers.ask.OllamaService") as mock_ollama_cls:
                        mock_ollama = MagicMock()
                        mock_ollama.chat = AsyncMock(return_value="Your balance is $100.50")
                        mock_ollama_cls.return_value = mock_ollama

                        await handle_ask_command(update, context)

                        mock_auth.assert_called_once_with(mock_session, 12345)
                        mock_ollama_cls.assert_called_once()
                        mock_ollama.chat.assert_called_once_with("What is my balance?")
                        update.message.reply_text.assert_called_once_with("Your balance is $100.50")

    @pytest.mark.asyncio
    async def test_handle_ask_admin_user(self):
        """Test handler creates OllamaService with admin flag."""
        from src.bot.handlers.ask import handle_ask_command

        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "/ask Create a period"
        update.message.from_user = MagicMock()
        update.message.from_user.id = 12345
        update.message.reply_text = AsyncMock()
        update.message.chat = MagicMock()
        update.message.chat.send_action = AsyncMock()
        context = MagicMock()

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_administrator = True

        with patch("src.bot.handlers.ask.is_llm_enabled", return_value=True):
            with patch("src.bot.handlers.ask.AsyncSessionLocal") as mock_session_cls:
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_cls.return_value = mock_session

                with patch("src.services.auth_service.get_authenticated_user") as mock_auth:
                    mock_auth.return_value = mock_user

                    with patch("src.bot.handlers.ask.OllamaService") as mock_ollama_cls:
                        mock_ollama = MagicMock()
                        mock_ollama.chat = AsyncMock(return_value="Period created")
                        mock_ollama_cls.return_value = mock_ollama

                        await handle_ask_command(update, context)

                        # Verify OllamaService was created with is_admin=True
                        call_kwargs = mock_ollama_cls.call_args[1]
                        assert call_kwargs["is_admin"] is True

    @pytest.mark.asyncio
    async def test_handle_ask_ollama_error(self):
        """Test handler handles Ollama errors gracefully."""
        from src.bot.handlers.ask import handle_ask_command

        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "/ask What is my balance?"
        update.message.from_user = MagicMock()
        update.message.from_user.id = 12345
        update.message.reply_text = AsyncMock()
        update.message.chat = MagicMock()
        update.message.chat.send_action = AsyncMock()
        context = MagicMock()

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_administrator = False

        with patch("src.bot.handlers.ask.is_llm_enabled", return_value=True):
            with patch("src.bot.handlers.ask.AsyncSessionLocal") as mock_session_cls:
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_cls.return_value = mock_session

                with patch("src.services.auth_service.get_authenticated_user") as mock_auth:
                    mock_auth.return_value = mock_user

                    with patch("src.bot.handlers.ask.OllamaService") as mock_ollama_cls:
                        mock_ollama = MagicMock()
                        mock_ollama.chat = AsyncMock(
                            side_effect=Exception("Ollama connection error")
                        )
                        mock_ollama_cls.return_value = mock_ollama

                        await handle_ask_command(update, context)

                        # Should have replied with error message about AI service
                        update.message.reply_text.assert_called_once()
                        call_args = update.message.reply_text.call_args[0][0]
                        assert "Sorry" in call_args or "couldn't process" in call_args

    @pytest.mark.asyncio
    async def test_handle_ask_sends_typing_indicator(self):
        """Test handler sends typing indicator before processing."""
        from src.bot.handlers.ask import handle_ask_command

        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "/ask What is my balance?"
        update.message.from_user = MagicMock()
        update.message.from_user.id = 12345
        update.message.reply_text = AsyncMock()
        update.message.chat = MagicMock()
        update.message.chat.send_action = AsyncMock()
        context = MagicMock()

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_administrator = False

        with patch("src.bot.handlers.ask.is_llm_enabled", return_value=True):
            with patch("src.bot.handlers.ask.AsyncSessionLocal") as mock_session_cls:
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_cls.return_value = mock_session

                with patch("src.services.auth_service.get_authenticated_user") as mock_auth:
                    mock_auth.return_value = mock_user

                    with patch("src.bot.handlers.ask.OllamaService") as mock_ollama_cls:
                        mock_ollama = MagicMock()
                        mock_ollama.chat = AsyncMock(return_value="Response")
                        mock_ollama_cls.return_value = mock_ollama

                        await handle_ask_command(update, context)

                        # Verify typing indicator was sent (handler uses string "typing")
                        update.message.chat.send_action.assert_called_once_with("typing")

    @pytest.mark.asyncio
    async def test_handle_ask_extracts_question_after_command(self):
        """Test handler extracts question correctly from command."""
        from src.bot.handlers.ask import handle_ask_command

        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "/ask   What is my current balance?  "
        update.message.from_user = MagicMock()
        update.message.from_user.id = 12345
        update.message.reply_text = AsyncMock()
        update.message.chat = MagicMock()
        update.message.chat.send_action = AsyncMock()
        context = MagicMock()

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_administrator = False

        with patch("src.bot.handlers.ask.is_llm_enabled", return_value=True):
            with patch("src.bot.handlers.ask.AsyncSessionLocal") as mock_session_cls:
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_cls.return_value = mock_session

                with patch("src.services.auth_service.get_authenticated_user") as mock_auth:
                    mock_auth.return_value = mock_user

                    with patch("src.bot.handlers.ask.OllamaService") as mock_ollama_cls:
                        mock_ollama = MagicMock()
                        mock_ollama.chat = AsyncMock(return_value="Response")
                        mock_ollama_cls.return_value = mock_ollama

                        await handle_ask_command(update, context)

                        # Should strip whitespace
                        mock_ollama.chat.assert_called_once_with("What is my current balance?")

    @pytest.mark.asyncio
    async def test_handle_ask_llm_disabled(self):
        """Test handler returns graceful message when LLM is disabled."""
        from src.bot.handlers.ask import handle_ask_command

        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "/ask What is my balance?"
        update.message.from_user = MagicMock()
        update.message.from_user.id = 12345
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        # Simulate OLLAMA_MODEL not being set
        with patch.dict("os.environ", {}, clear=False):
            # Ensure OLLAMA_MODEL is not set
            with patch("src.bot.handlers.ask.is_llm_enabled", return_value=False):
                await handle_ask_command(update, context)

                # Should reply with disabled message
                update.message.reply_text.assert_called_once()
                # OllamaService should never be instantiated
                # The reply should use localized t("errors.llm_disabled")

    @pytest.mark.asyncio
    async def test_is_llm_enabled_with_model(self):
        """Test is_llm_enabled returns True when OLLAMA_MODEL is set."""
        from src.bot.handlers.ask import is_llm_enabled

        with patch.dict("os.environ", {"OLLAMA_MODEL": "qwen2.5:1.5b"}):
            assert is_llm_enabled() is True

    @pytest.mark.asyncio
    async def test_is_llm_enabled_without_model(self):
        """Test is_llm_enabled returns False when OLLAMA_MODEL is not set."""
        from src.bot.handlers.ask import is_llm_enabled

        with patch.dict("os.environ", {}, clear=True):
            assert is_llm_enabled() is False
