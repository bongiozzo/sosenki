"""Handler for /ask command - natural language AI assistant.

Provides conversational AI access to SOSenki data using Ollama with tool calling.
Users can ask questions about their balance, bills, and periods in natural language.
"""

import logging
import os

from telegram import Update
from telegram.ext import ContextTypes

from src.services import AsyncSessionLocal
from src.services.llm_service import OllamaService
from src.services.localizer import t

logger = logging.getLogger(__name__)


def is_llm_enabled() -> bool:
    """Check if LLM feature is enabled (OLLAMA_MODEL is set)."""
    return bool(os.getenv("OLLAMA_MODEL"))


async def handle_ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ask command for natural language queries.

    Usage:
        /ask What is my balance?
        /ask Show me my recent bills
        /ask Tell me about service period 1

    The command uses Ollama to process natural language and fetch
    relevant data using tool calling. User context is automatically
    injected for balance/bills queries.

    Args:
        update: Telegram update object
        context: Bot context with user data
    """
    try:
        # Validate update
        if not update.message or not update.message.from_user:
            logger.warning("Received /ask without message or user")
            return

        telegram_id = update.message.from_user.id
        message_text = update.message.text or ""

        # Check if LLM feature is enabled
        if not is_llm_enabled():
            await update.message.reply_text(t("errors.llm_disabled"))
            return

        # Extract the question (everything after /ask)
        parts = message_text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await update.message.reply_text(
                "Please provide a question after /ask.\n\n"
                "Examples:\n"
                "• /ask What is my balance?\n"
                "• /ask Show me my recent bills\n"
                "• /ask Tell me about the current service period"
            )
            return

        question = parts[1].strip()

        # Authenticate user
        # Import here to avoid circular import (auth_service -> bot_config -> bot/__init__)
        from src.services.auth_service import get_authenticated_user

        async with AsyncSessionLocal() as session:
            try:
                user = await get_authenticated_user(session, telegram_id)
            except Exception as e:
                logger.warning(f"Auth failed for telegram_id={telegram_id}: {e}")
                await update.message.reply_text(t("errors.not_authorized"))
                return

            # Send typing indicator while processing
            await update.message.chat.send_action("typing")

            # Initialize Ollama service with user context
            ollama = OllamaService(
                session=session,
                user_id=user.id,
                is_admin=user.is_administrator,
            )

            logger.info(
                f"Processing /ask from user_id={user.id} (admin={user.is_administrator}): {question[:50]}..."
            )

            # Get AI response
            try:
                response = await ollama.chat(question)
            except Exception as e:
                logger.error(f"Ollama chat error: {e}", exc_info=True)
                await update.message.reply_text(
                    "Sorry, I couldn't process your question. "
                    "Please make sure the AI service is running and try again."
                )
                return

            # Send response
            await update.message.reply_text(response)

            logger.info(f"Sent AI response to user_id={user.id}, length={len(response)}")

    except Exception as e:
        logger.error(f"Error in /ask handler: {e}", exc_info=True)
        try:
            await update.message.reply_text(t("errors.error_processing"))
        except Exception:
            pass


__all__ = ["handle_ask_command"]
