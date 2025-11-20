"""Unit tests for parsers module."""

from datetime import date
from decimal import Decimal

import pytest

from src.services.parsers import (
    parse_boolean,
    parse_date,
    parse_russian_currency,
    parse_russian_decimal,
    parse_russian_percentage,
)


class TestParseDate:
    """Tests for parse_date function."""

    def test_parse_valid_date(self):
        """Test parsing a valid Russian date format."""
        result = parse_date("23.06.2025")
        assert result == date(2025, 6, 23)

    def test_parse_another_valid_date(self):
        """Test parsing another valid date."""
        result = parse_date("01.01.2024")
        assert result == date(2024, 1, 1)

    def test_parse_empty_string(self):
        """Test parsing an empty string returns None."""
        result = parse_date("")
        assert result is None

    def test_parse_none(self):
        """Test parsing None returns None."""
        result = parse_date(None)
        assert result is None

    def test_parse_whitespace_only(self):
        """Test parsing whitespace-only string returns None."""
        result = parse_date("   ")
        assert result is None

    def test_parse_invalid_format(self):
        """Test parsing invalid date format raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse date"):
            parse_date("2025-06-23")  # Wrong format (YYYY-MM-DD instead of DD.MM.YYYY)

    def test_parse_invalid_date(self):
        """Test parsing invalid date raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse date"):
            parse_date("32.13.2025")  # Invalid day and month


class TestParseRussianDecimal:
    """Tests for parse_russian_decimal function."""

    def test_parse_with_comma(self):
        """Test parsing decimal with comma separator."""
        result = parse_russian_decimal("1 000,25")
        assert result == Decimal("1000.25")

    def test_parse_simple_decimal(self):
        """Test parsing simple decimal."""
        result = parse_russian_decimal("2,5")
        assert result == Decimal("2.5")

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        result = parse_russian_decimal("")
        assert result is None


class TestParseRussianPercentage:
    """Tests for parse_russian_percentage function."""

    def test_parse_percentage(self):
        """Test parsing percentage with % suffix."""
        result = parse_russian_percentage("3,85%")
        assert result == Decimal("3.85")

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        result = parse_russian_percentage("")
        assert result is None


class TestParseRussianCurrency:
    """Tests for parse_russian_currency function."""

    def test_parse_currency_with_ruble_symbol(self):
        """Test parsing currency with ruble symbol."""
        result = parse_russian_currency("р.7 000 000,00")
        assert result == Decimal("7000000.00")

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        result = parse_russian_currency("")
        assert result is None


class TestParseBoolean:
    """Tests for parse_boolean function."""

    def test_parse_yes(self):
        """Test parsing Russian 'yes' returns True."""
        assert parse_boolean("Да") is True

    def test_parse_no(self):
        """Test parsing Russian 'no' returns False."""
        assert parse_boolean("Нет") is False

    def test_parse_empty(self):
        """Test parsing empty string returns False."""
        assert parse_boolean("") is False

    def test_parse_none(self):
        """Test parsing None returns False."""
        assert parse_boolean(None) is False
