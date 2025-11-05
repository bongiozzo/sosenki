"""Telegram bot configuration from environment variables."""

import os

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class BotConfig(BaseSettings):
    """Bot configuration loaded from environment."""

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # Allow extra fields in .env file
    )

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    admin_telegram_id: str = os.getenv("ADMIN_TELEGRAM_ID", "")
    
    # Mini App configuration (002-welcome-mini-app)
    telegram_mini_app_id: str = os.getenv("TELEGRAM_MINI_APP_ID", "")
    mini_app_url: str = os.getenv("MINI_APP_URL", "")

    def validate(self) -> None:
        """Validate required configuration is present."""
        if not self.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        if not self.admin_telegram_id:
            raise ValueError("ADMIN_TELEGRAM_ID environment variable is required")


# Load and validate config
bot_config = BotConfig()
bot_config.validate()

__all__ = ["BotConfig", "bot_config"]
