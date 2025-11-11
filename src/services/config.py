"""Configuration loading for database seeding.

Loads settings from .env file and environment variables with sensible defaults.
Validates required configuration and provides clear error messages.
"""

import json
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
        ValueError: If required configuration is missing or invalid

    Example:
        Create .env file:
        ```
        GOOGLE_SHEET_ID=your-google-sheet-id-here
        GOOGLE_CREDENTIALS_PATH=.vscode/google_credentials.json
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
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", ".vscode/google_credentials.json")
    database_url = os.getenv("DATABASE_URL", "sqlite:///./sostenki.db")
    log_file = os.getenv("LOG_FILE", "logs/seed.log")

    # Validate GOOGLE_SHEET_ID
    if not google_sheet_id:
        raise ValueError(
            "GOOGLE_SHEET_ID not configured. "
            "Set GOOGLE_SHEET_ID environment variable or in .env file"
        )

    # Validate credentials file exists (T031)
    credentials_file = Path(credentials_path)
    if not credentials_file.exists():
        raise ValueError(
            f"Credentials file not found: {credentials_path}. "
            f"Ensure service account JSON is at this path."
        )

    # Validate credentials file is valid JSON (T031)
    try:
        with open(credentials_file, "r") as f:
            credentials_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Credentials file is not valid JSON: {credentials_path}. "
            f"Error: {str(e)}"
        ) from e
    except OSError as e:
        raise ValueError(
            f"Cannot read credentials file: {credentials_path}. "
            f"Error: {str(e)}"
        ) from e

    # Validate credentials contain required Google service account fields (T033)
    required_fields = {"type", "project_id", "private_key", "client_email"}
    missing_fields = required_fields - set(credentials_data.keys())
    if missing_fields:
        raise ValueError(
            f"Credentials file missing required fields: {', '.join(missing_fields)}. "
            f"Ensure this is a valid Google service account JSON file."
        )

    # Validate private key format (T033)
    private_key = credentials_data.get("private_key", "")
    if not private_key.startswith("-----BEGIN RSA PRIVATE KEY-----"):
        raise ValueError(
            "Credentials file contains invalid private key format. "
            "Ensure this is a valid Google service account JSON file."
        )

    return SeedConfig(
        google_sheet_id=google_sheet_id,
        credentials_path=credentials_path,
        database_url=database_url,
        log_file=log_file,
    )
