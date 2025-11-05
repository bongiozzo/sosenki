#!/usr/bin/env python
"""Manual test to verify bot receives and processes Telegram messages."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.bot import create_bot_app
from src.bot.config import bot_config
from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_bot_message_handling():
    """Test that bot receives and processes messages."""
    try:
        # Create bot app
        bot_app = await create_bot_app()
        logger.info("✅ Bot app created successfully")

        # Initialize the bot application (required before polling)
        logger.info("Initializing bot...")
        await bot_app.initialize()
        logger.info("✅ Bot initialized")

        # Start bot in polling mode
        logger.info("Starting bot polling...")
        await bot_app.start()
        await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("✅ Bot polling started - listening for messages")
        logger.info(f"Admin Telegram ID: {bot_config.admin_telegram_id}")
        logger.info(f"Bot Token: {bot_config.telegram_bot_token[:10]}...")

        # Keep polling for 60 seconds
        await asyncio.sleep(60)

        # Stop polling
        await bot_app.updater.stop()
        await bot_app.stop()
        logger.info("✅ Bot polling stopped")

    except Exception as e:
        logger.error(f"❌ Error during bot test: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_bot_message_handling())
