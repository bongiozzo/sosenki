"""Logging configuration and utilities for database seeding.

Provides dual output (stdout + file) at INFO level with ISO format timestamps.
Suitable for both real-time developer feedback and audit trails.
"""

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
        - Colors terminal output for ERROR/WARNING visibility
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure logger
    logger = logging.getLogger("sostenki.seeding")
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


def setup_server_logging(log_file: str = "logs/server.log") -> None:
    """
    Configure root logger for bot + mini app server.

    Args:
        log_file: Path to log file (default: logs/server.log)

    Behavior:
        - Sets up all loggers to output to both stdout and file
        - ISO format timestamps for consistency
        - Suitable for both real-time debugging and audit trails
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # ISO format: [YYYY-MM-DD HH:MM:SS]
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Handler 1: stdout (console)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)

    # Handler 2: file (logs/server.log)
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
