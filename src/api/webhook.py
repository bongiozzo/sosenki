"""FastAPI webhook endpoint for Telegram updates."""

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from telegram import Update
from telegram.ext import Application

logger = logging.getLogger(__name__)

# FastAPI instance (will be initialized in main.py)
app = FastAPI(
    title="SOSenki Bot",
    description="Client Request Approval Workflow - Telegram Bot",
    version="0.1.0",
)

# Mount static files for Mini App (002-welcome-mini-app)
static_path = Path(__file__).parent.parent / "static" / "mini_app"
if static_path.exists():
    app.mount("/mini-app", StaticFiles(directory=str(static_path), html=True), name="mini-app")
    logger.info(f"Mounted Mini App static files from {static_path}")

# Include Mini App API router
from src.api.mini_app import router as mini_app_router
app.include_router(mini_app_router)

# Include Payment Management API router (T116)
from src.api.payment import router as payment_router
app.include_router(payment_router)

# Global bot application reference (will be set via setup_webhook_route or dependency)
_bot_app: Optional[Application] = None


def get_bot_app() -> Application:
    """Get the bot application from dependency injection or global."""
    global _bot_app
    if not _bot_app:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    return _bot_app


async def setup_webhook_route(fastapi_app: FastAPI, bot_app: Application) -> None:
    """Register webhook endpoint with FastAPI.

    Args:
        fastapi_app: FastAPI application instance
        bot_app: Telegram bot Application instance
    """
    global _bot_app
    _bot_app = bot_app

    # Remove the old endpoint and add a new one with the bot_app in closure
    # This is a workaround for the global variable issue
    @fastapi_app.post("/webhook/telegram")
    async def telegram_webhook(update: dict) -> dict:
        """Receive Telegram updates and dispatch to bot handlers.

        Args:
            update: Telegram Update object (as JSON)

        Returns:
            {"ok": True} response as per Telegram webhook protocol
        """
        try:
            # Convert dict to Telegram Update object
            telegram_update = Update.de_json(update, bot_app.bot)
            if telegram_update:
                # Process update through bot application
                await bot_app.process_update(telegram_update)
            return {"ok": True}
        except Exception as e:
            logger.error("Error processing update: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error") from e


# Register health check endpoint directly (always available)
@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint for monitoring."""
    return {"status": "ok"}


# Register webhook endpoint that uses the global _bot_app (T033)
@app.post("/webhook/telegram")
async def telegram_webhook_handler(update: dict) -> dict:
    """Receive Telegram updates and dispatch to bot handlers.

    T033, T034: Process Telegram updates through bot handlers with logging.

    This endpoint uses the global _bot_app which is set by setup_webhook_route
    or can be set directly for testing.
    """
    global _bot_app
    if not _bot_app:
        logger.error("Bot application not initialized")
        raise HTTPException(status_code=503, detail="Bot not initialized")
    try:
        # T034: Log incoming update
        logger.debug("Received Telegram webhook update")

        # Convert dict to Telegram Update object
        telegram_update = Update.de_json(update, _bot_app.bot)
        if telegram_update:
            # Log the type of update received
            if telegram_update.message:
                logger.info(
                    "Processing message from user %s: %s",
                    telegram_update.message.from_user.id,
                    (telegram_update.message.text[:50]
                     if telegram_update.message.text else "")
                )
            # T033: Process update through bot application (dispatches to handlers)
            await _bot_app.process_update(telegram_update)
        return {"ok": True}
    except Exception as e:
        logger.error("Error processing update: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


__all__ = ["app", "setup_webhook_route"]



