"""Tests for logging service configuration."""

import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.services.logging import setup_server_logging


class TestServerLogging:
    """Test server logging configuration."""

    def setup_method(self):
        """Save original handlers before each test."""
        self.root_logger = logging.getLogger()
        self.original_handlers = self.root_logger.handlers.copy()
        self.original_level = self.root_logger.level

    def teardown_method(self):
        """Restore original handlers after each test."""
        self.root_logger = logging.getLogger()
        # Remove all handlers
        for handler in self.root_logger.handlers[:]:
            handler.close()
            self.root_logger.removeHandler(handler)
        # Restore originals
        for handler in self.original_handlers:
            self.root_logger.addHandler(handler)
        # Restore original level
        self.root_logger.setLevel(self.original_level)

    def test_setup_server_logging_creates_log_directory(self) -> None:
        """Verify setup_server_logging creates logs directory if missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test_logs" / "server.log"

            # Directory should not exist yet
            assert not log_file.parent.exists()

            # Setup logging
            setup_server_logging(str(log_file))

            # Directory should now exist
            assert log_file.parent.exists()

    def test_setup_server_logging_creates_handlers(self) -> None:
        """Verify setup_server_logging creates both stdout and file handlers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "server.log"

            setup_server_logging(str(log_file))

            # Should have 2 handlers (stdout + file)
            assert len(self.root_logger.handlers) == 2

    def test_setup_server_logging_sets_info_level(self) -> None:
        """Verify setup_server_logging sets log level to INFO by default."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "server.log"

            # Mock LOG_LEVEL to ensure consistent test behavior
            with patch.dict("os.environ", {"LOG_LEVEL": "INFO"}, clear=False):
                setup_server_logging(str(log_file))

                assert self.root_logger.level == logging.INFO

    def test_setup_server_logging_handler_levels(self) -> None:
        """Verify both handlers are set to configured level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "server.log"

            # Mock LOG_LEVEL to ensure consistent test behavior
            with patch.dict("os.environ", {"LOG_LEVEL": "INFO"}, clear=False):
                setup_server_logging(str(log_file))

                for handler in self.root_logger.handlers:
                    assert handler.level == logging.INFO

    def test_setup_server_logging_writes_to_file(self) -> None:
        """Verify setup_server_logging writes log messages to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "server.log"

            setup_server_logging(str(log_file))

            # Log a test message
            test_logger = logging.getLogger("test.module")
            test_message = "Test log message"
            test_logger.info(test_message)

            # Verify file exists and contains message
            assert log_file.exists()
            log_contents = log_file.read_text()
            assert test_message in log_contents

    def test_setup_server_logging_formatter_has_timestamp(self) -> None:
        """Verify log formatter includes ISO timestamps."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "server.log"

            setup_server_logging(str(log_file))

            # Log a test message
            test_logger = logging.getLogger("test.timestamp")
            test_logger.info("Timestamp test")

            # Verify ISO format timestamp in log
            log_contents = log_file.read_text()
            # ISO format: [YYYY-MM-DD HH:MM:SS]
            assert "[202" in log_contents  # Year starts with 202x

    def test_setup_server_logging_formatter_includes_logger_name(self) -> None:
        """Verify log formatter includes logger name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "server.log"

            setup_server_logging(str(log_file))

            # Log with specific logger name
            test_logger = logging.getLogger("custom.logger")
            test_logger.info("Test message")

            # Verify logger name in output
            log_contents = log_file.read_text()
            assert "custom.logger" in log_contents

    def test_setup_server_logging_formatter_includes_level(self) -> None:
        """Verify log formatter includes log level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "server.log"

            setup_server_logging(str(log_file))

            # Log at different levels
            test_logger = logging.getLogger("test.level")
            test_logger.info("Info message")
            test_logger.warning("Warning message")

            log_contents = log_file.read_text()
            assert "INFO" in log_contents
            assert "WARNING" in log_contents

    def test_setup_server_logging_removes_existing_handlers(self) -> None:
        """Verify setup_server_logging clears existing handlers to avoid duplicates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "server.log"

            # Add a dummy handler to root logger
            dummy_handler = logging.StreamHandler()
            self.root_logger.addHandler(dummy_handler)

            setup_server_logging(str(log_file))

            # Should have 2 new handlers (stdout + file), not including the dummy
            assert len(self.root_logger.handlers) == 2
            setup_server_logging(str(log_file))

            # Should have exactly 2 handlers (not 3+)
            assert len(self.root_logger.handlers) == 2
            assert dummy_handler not in self.root_logger.handlers
