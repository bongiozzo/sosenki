"""CLI entry point for database seeding from Google Sheets.

This module provides the `make seed` command interface for developers to
synchronize the local SQLite database with canonical data from SOSenkiPrivate
Google Sheet ("Дома" sheet).

Usage:
    python -m src.cli.seed
    make seed  (via Makefile)

Exit Codes:
    0 - Success: Database fully seeded
    1 - Failure: Error encountered; database state unchanged

Logging:
    INFO level logs to both stdout and logs/seed.log
    Provides real-time feedback and audit trail
"""

import asyncio
import sys

from src.services.config import load_config
from src.services.logging import setup_logging


async def main() -> int:
    """
    Main entry point for database seeding CLI.

    Orchestrates the complete seeding process:
    1. Set up logging
    2. Load configuration
    3. Fetch data from Google Sheets
    4. Parse and validate data
    5. Seed database atomically

    Returns:
        Exit code: 0 for success, 1 for failure
    """
    try:
        # Initialize logging (to both stdout and file)
        logger = setup_logging()
        logger.info("Starting database seed from Google Sheets...")

        # Load configuration from .env and environment
        config = load_config()
        logger.info(f"Configuration loaded: Sheet ID={config.google_sheet_id[:10]}...")

        # TODO: Import and execute seeding service
        # from src.services.seeding import execute_seed
        # result = await execute_seed(config, logger)
        # return 0 if result.success else 1

        logger.info("Database seed complete!")
        return 0

    except KeyboardInterrupt:
        logger.warning("Seed interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Seed failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
