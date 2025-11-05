"""Main application entry point."""

import asyncio
import logging
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from telegram.ext import Application

from src.api.webhook import app, setup_webhook_route
from src.bot import create_bot_app

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global bot application instance
bot_app: Optional[Application] = None


async def initialize_bot() -> None:
    """Initialize and setup the Telegram bot."""
    global bot_app
    logger.info("Initializing Telegram bot...")
    bot_app = await create_bot_app()

    # Register handlers (currently stubs)
    # TODO: T032 - Register /request command handler
    # TODO: T044 - Register admin approval handler
    # TODO: T052 - Register admin rejection handler

    logger.info("Bot initialized successfully")


async def startup_event():
    """FastAPI startup event - initialize bot and setup webhook."""
    await initialize_bot()
    if bot_app:
        await setup_webhook_route(app, bot_app)
        logger.info("Webhook route registered")


async def shutdown_event():
    """FastAPI shutdown event - cleanup bot."""
    if bot_app:
        await bot_app.stop()
        logger.info("Bot stopped")


# Register startup/shutdown events
app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)


async def run_webhook_mode(host: str = "0.0.0.0", port: int = 8000):
    """Run application in webhook mode (production)."""
    logger.info(f"Starting bot in webhook mode on {host}:{port}")
    await initialize_bot()
    if bot_app:
        await setup_webhook_route(app, bot_app)

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def run_polling_mode():
    """Run application in polling mode (development)."""
    logger.info("Starting bot in polling mode...")
    global bot_app
    bot_app = await create_bot_app()

    # Start polling (for development)
    async with bot_app:
        await bot_app.start()
        logger.info("Bot started (polling)")
        # Keep polling running indefinitely
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user (KeyboardInterrupt)")
        finally:
            await bot_app.stop()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SOSenki Bot")
    parser.add_argument(
        "--mode",
        choices=["webhook", "polling"],
        default="webhook",
        help="Run mode (default: webhook)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")

    args = parser.parse_args()

    if args.mode == "webhook":
        asyncio.run(run_webhook_mode(args.host, args.port))
    else:  # polling
        asyncio.run(run_polling_mode())


if __name__ == "__main__":
    main()
