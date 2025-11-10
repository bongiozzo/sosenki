"""Configuration loading for database seeding.

Loads settings from .env file and environment variables with sensible defaults.
Validates required configuration and provides clear error messages.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class SeedConfig:
    """Configuration for database seeding process."""

    google_sheet_id: str
    """Google Sheet ID to fetch data from (required)"""

    credentials_path: str
    """Path to service account credentials JSON file (required)"""

    database_url: str = "sqlite:///./sostenki.db"
    """SQLAlchemy database URL (default: local SQLite)"""

    log_file: str = "logs/seed.log"
    """Path to log file (default: logs/seed.log)"""

    app_is_offline: bool = True
    """Safety flag: seed requires app to be offline (default: True)"""


def load_config() -> SeedConfig:
    """
    Load configuration from .env file and environment variables.

    Priority (highest to lowest):
    1. Environment variables (GOOGLE_SHEET_ID, CREDENTIALS_PATH, DATABASE_URL, etc.)
    2. .env file in project root
    3. Default values

    Returns:
        SeedConfig with all required settings

    Raises:
        ValueError: If required configuration is missing

    Example:
        Create .env file:
        ```
        GOOGLE_SHEET_ID=1c-WZhVdCV01QE0cgk7yodDC58rMov-KKp-IWiveTTaE
        CREDENTIALS_PATH=sosenkimcp-8b756c9d2720.json
        ```

        Then call:
        ```
        config = load_config()
        ```
    """
    # Load .env file from project root
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path)

    # Read configuration
    google_sheet_id = os.getenv("GOOGLE_SHEET_ID")
    credentials_path = os.getenv("CREDENTIALS_PATH", "sosenkimcp-8b756c9d2720.json")
    database_url = os.getenv("DATABASE_URL", "sqlite:///./sostenki.db")
    log_file = os.getenv("LOG_FILE", "logs/seed.log")

    # Validate required configuration
    if not google_sheet_id:
        raise ValueError(
            "GOOGLE_SHEET_ID not configured. "
            "Set GOOGLE_SHEET_ID environment variable or in .env file"
        )

    # Check if credentials file exists
    if not Path(credentials_path).exists():
        raise ValueError(
            f"Credentials file not found: {credentials_path}. "
            f"Ensure service account JSON is at this path."
        )

    return SeedConfig(
        google_sheet_id=google_sheet_id,
        credentials_path=credentials_path,
        database_url=database_url,
        log_file=log_file,
    )
