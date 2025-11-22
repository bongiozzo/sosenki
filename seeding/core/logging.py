"""Logging configuration for seeding operations."""

import logging
import sys
from pathlib import Path


def setup_logging(log_file: str = "logs/seed.log") -> logging.Logger:
    """
    Set up logging with dual handlers (stdout + file).

    Args:
        log_file: Path to log file (relative to project root)

    Returns:
        Configured logger instance at INFO level

    Behavior:
        - Logs all messages at INFO level and above
        - Prints to stdout for real-time feedback
        - Writes to logs/seed.log for audit trail
        - ISO format timestamps: [2025-11-10 14:32:01]
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure logger
    logger = logging.getLogger("sosenki.seeding")
    logger.setLevel(logging.INFO)

    # Remove any existing handlers
    logger.handlers.clear()

    # ISO format: [YYYY-MM-DD HH:MM:SS]
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler 1: stdout (console)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    # Handler 2: file (logs/seed.log)
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
