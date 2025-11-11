"""Main application entry point."""

import asyncio
import logging
import os
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from telegram.ext import Application

from src.api.webhook import app, setup_webhook_route
from src.bot import create_bot_app
from src.services.logging import setup_server_logging

# Load environment variables
load_dotenv()

# Configure logging (with file logging)
setup_server_logging()
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


async def run_webhook_mode(host: str = "0.0.0.0", port: int = 8000):
    """Run application in webhook mode (production)."""
    logger.info(f"Starting bot in webhook mode on {host}:{port}")
    
    global bot_app
    
    # Create but don't initialize bot yet - will be done in FastAPI startup
    bot_app = await create_bot_app()
    
    # Setup webhook route with the bot app
    await setup_webhook_route(app, bot_app)
    
    # Add custom startup handler to initialize bot after Uvicorn binds port
    async def init_bot_on_startup():
        global bot_app
        if bot_app:
            logger.info("Initializing bot Application on FastAPI startup...")
            await bot_app.initialize()
            logger.info("Bot Application initialized")
            
            # Register webhook URL with Telegram
            webhook_url = os.getenv("WEBHOOK_URL", "").strip()
            if webhook_url:
                logger.info(f"Setting Telegram webhook to {webhook_url}")
                try:
                    await bot_app.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
                    logger.info("Webhook registered successfully with Telegram")
                except Exception as e:
                    logger.error(f"Failed to set webhook: {e}", exc_info=True)
            else:
                logger.warning("WEBHOOK_URL not set in environment")
    
    async def shutdown_bot():
        global bot_app
        if bot_app:
            try:
                await bot_app.shutdown()
                logger.info("Bot Application shutdown complete")
            except Exception as e:
                logger.error(f"Error shutting down bot: {e}")
    
    # Register startup/shutdown with FastAPI
    app.add_event_handler("startup", init_bot_on_startup)
    app.add_event_handler("shutdown", shutdown_bot)

    logger.info(f"Starting Uvicorn server on {host}:{port}...")
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def run_polling_mode_with_api(host: str = "0.0.0.0", port: int = 8000):
    """Run bot in polling mode AND FastAPI server for Mini App.
    
    This is needed for local development with localtunnel:
    - Bot uses polling (doesn't need HTTP server)
    - FastAPI server serves Mini App on port 8000
    - localtunnel exposes port 8000 to internet
    """
    logger.info(f"Starting bot in polling mode with API server on {host}:{port}...")
    global bot_app
    bot_app = await create_bot_app()

    # Initialize bot
    logger.info("Initializing bot...")
    await bot_app.initialize()
    logger.info("Bot initialized")

    # Setup webhook route for FastAPI
    await setup_webhook_route(app, bot_app)

    # Start bot
    logger.info("Starting bot polling...")
    await bot_app.start()
    
    # Start FastAPI server in background task
    async def run_uvicorn():
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()

    # Start polling in background task
    async def run_bot_polling():
        await bot_app.updater.start_polling(
            allowed_updates=None,  # Get all updates
            drop_pending_updates=False,  # Don't skip pending updates
        )

    # Run both bot polling and API server concurrently
    try:
        await asyncio.gather(
            run_uvicorn(),
            run_bot_polling(),
        )
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user (KeyboardInterrupt)")
    finally:
        await bot_app.updater.stop()
        await bot_app.stop()
        logger.info("Bot stopped")


async def run_polling_mode():
    """Run application in polling mode (development)."""
    logger.info("Starting bot in polling mode...")
    global bot_app
    bot_app = await create_bot_app()

    # Start polling (for development)
    logger.info("Initializing bot...")
    await bot_app.initialize()
    logger.info("Bot initialized")

    logger.info("Starting bot polling...")
    await bot_app.start()
    await bot_app.updater.start_polling(
        allowed_updates=None,  # Get all updates
        drop_pending_updates=False,  # Don't skip pending updates
    )
    logger.info("Bot started (polling)")

    # Keep polling running indefinitely
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user (KeyboardInterrupt)")
    finally:
        await bot_app.updater.stop()
        await bot_app.stop()
        logger.info("Bot stopped")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SOSenki Bot")
    parser.add_argument(
        "--mode",
        choices=["webhook", "polling", "polling-api"],
        default=None,  # Auto-detect based on environment
        help="Run mode (default: auto-detect)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")

    args = parser.parse_args()

    # Auto-detect mode if not specified
    mode = args.mode
    if mode is None:
        # Check if running locally (localhost webhook URL or no explicit webhook URL)
        webhook_url = os.getenv("WEBHOOK_URL", "").strip()
        is_local = (
            not webhook_url
            or "localhost" in webhook_url
            or "127.0.0.1" in webhook_url
            or webhook_url == "https://your-domain.com/webhook/telegram"
        )
        # For local dev with localtunnel/ngrok, use polling-api to serve Mini App
        has_mini_app_url = bool(os.getenv("MINI_APP_URL", "").strip())
        mode = "polling-api" if (is_local and has_mini_app_url) else ("polling" if is_local else "webhook")
        logger.info(f"Auto-detected mode: {mode} (webhook_url={webhook_url}, mini_app_url={os.getenv('MINI_APP_URL')})")

    if mode == "webhook":
        asyncio.run(run_webhook_mode(args.host, args.port))
    elif mode == "polling-api":
        asyncio.run(run_polling_mode_with_api(args.host, args.port))
    else:  # polling
        asyncio.run(run_polling_mode())


if __name__ == "__main__":
    main()
