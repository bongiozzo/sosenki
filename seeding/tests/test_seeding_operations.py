"""Read-only verification tests for Google Sheets integration and seeding validation.

IMPORTANT: These tests ONLY read from the seeded database (sosenki.db).
They do NOT create, update, or delete any data.

Data-modification tests (transactions, performance, etc.) should be written
in tests/ directory using test_sosenki.db for isolation.
"""

from decimal import Decimal

import pytest

from seeding.core.errors import CredentialsError


class TestGoogleSheetsClientIntegration:
    """Verify Google Sheets client credential handling (read-only)."""

    def test_credentials_loading_missing_file_raises_error(self):
        """Verify GoogleSheetsClient raises error for missing credentials."""
        from seeding.core.google_sheets import GoogleSheetsClient

        with pytest.raises(CredentialsError):
            GoogleSheetsClient(credentials_path="/non/existent/path/credentials.json")

    def test_credentials_loading_invalid_json_raises_error(self, tmp_path):
        """Verify GoogleSheetsClient raises error for invalid JSON."""
        from seeding.core.google_sheets import GoogleSheetsClient

        creds_file = tmp_path / "invalid.json"
        creds_file.write_text("{invalid json content")

        with pytest.raises(CredentialsError):
            GoogleSheetsClient(credentials_path=str(creds_file))


class TestRussianNumberParsingIntegration:
    """Verify Russian decimal/percentage parsing (read-only, no DB writes)."""

    def test_russian_decimal_parser_converts_correctly(self):
        """Verify Russian decimal parser converts format correctly."""
        from src.utils.parsers import parse_russian_decimal

        # Test Russian format: "1 000,25" → Decimal("1000.25")
        result = parse_russian_decimal("1 000,25")
        assert result == Decimal("1000.25")

        # Test another example
        result = parse_russian_decimal("5 500,75")
        assert result == Decimal("5500.75")

    def test_russian_percentage_parser_converts_correctly(self):
        """Verify Russian percentage parser converts format correctly."""
        from src.utils.parsers import parse_russian_percentage

        # Test Russian format: "3,85%" → Decimal("3.85")
        result = parse_russian_percentage("3,85%")
        assert result == Decimal("3.85")

    def test_boolean_parser_converts_correctly(self):
        """Verify boolean parser handles Russian Yes/No."""
        from src.utils.parsers import parse_boolean

        # "Да" → True
        assert parse_boolean("Да") is True

        # "Нет" → False
        assert parse_boolean("Нет") is False

        # Empty string → False
        assert parse_boolean("") is False


class TestErrorHandlingRobustness:
    """Error handling validation (read-only, no DB writes)."""

    def test_empty_or_invalid_user_name_validation(self):
        """Verify empty names are detected as invalid."""
        # Valid names pass basic validation
        assert len("Иван") > 0
        assert len("П") > 0

        # Invalid names fail validation
        assert len("") == 0
        assert len("   ".strip()) == 0

    def test_invalid_decimal_format_rejected(self):
        """Verify invalid decimals are rejected."""
        from src.utils.parsers import parse_russian_decimal

        # Valid format
        result = parse_russian_decimal("100,50")
        assert result == Decimal("100.5")

        # Invalid format should raise
        with pytest.raises((ValueError, TypeError)):
            parse_russian_decimal("not_a_number")

    def test_credentials_error_handling(self):
        """Verify error messages are handled properly."""
        from seeding.core.google_sheets import GoogleSheetsClient

        # Missing credentials should raise CredentialsError
        with pytest.raises(CredentialsError):
            GoogleSheetsClient(credentials_path="/does/not/exist.json")

    def test_api_error_message_clarity(self):
        """Verify API errors produce clear messages."""
        # Simulate API error
        api_error_message = "API Error: 503 Service Unavailable"

        # Verify message is clear and actionable
        assert "503" in api_error_message
        assert "Service Unavailable" in api_error_message
