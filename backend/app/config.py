"""Application configuration from environment variables."""

from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = Field(
        default="postgresql://sosenki_user:sosenki_password@localhost:5432/sosenki",
        description="PostgreSQL connection string",
    )
    database_echo: bool = Field(default=False, description="Log SQL queries")

    # Telegram
    telegram_bot_token: str = Field(
        default="test_bot_token", description="Telegram bot token for notifications"
    )
    telegram_admin_group_chat_id: int = Field(
        default=-1001234567890, description="Telegram admin group chat ID for request notifications"
    )

    # Mini App
    initdata_max_age_seconds: int = Field(
        default=120, description="Maximum age of initData auth_date in seconds"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # API
    api_title: str = Field(default="SOSenki API", description="API title")
    api_version: str = Field(default="0.1.0", description="API version")


# Global settings instance
settings = Settings()
