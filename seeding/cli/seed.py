"""CLI entry point for database seeding from Google Sheets.

This module provides the `make seed` command interface for developers to
synchronize the local SQLite database with canonical data from Google Sheets.

Usage:
    python -m seeding.cli.seed
    make seed  (via Makefile)

Exit Codes:
    0 - Success: Database fully seeded
    1 - Failure: Error encountered; database state unchanged

Logging:
    INFO level logs to both stdout and logs/seed.log
    Provides real-time feedback and audit trail
"""

import asyncio
import os
import sys

from seeding.core.logging import setup_logging


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

        # Load Google Sheets configuration from environment
        google_sheet_id = os.getenv("GOOGLE_SHEET_ID")
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", ".vscode/google_credentials.json")

        if not google_sheet_id:
            logger.error("GOOGLE_SHEET_ID environment variable not set")
            return 1

        logger.info(f"Configuration loaded: Sheet ID={google_sheet_id[:10]}...")

        # Execute database seeding
        from seeding.core.google_sheets import GoogleSheetsClient
        from seeding.core.seeding import SeededService
        from src.services import SessionLocal

        db = SessionLocal()
        try:
            google_sheets_client = GoogleSheetsClient(credentials_path)
            seeding_service = SeededService(db, logger)
            result = seeding_service.execute_seed(
                google_sheets_client,
                google_sheet_id,
            )

            # Output summary report
            logger.info("\n" + result.get_summary_report())

            return 0 if result.success else 1
        finally:
            db.close()

    except KeyboardInterrupt:
        logger.warning("Seed interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Seed failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
