"""Russian data type parsing utilities for Google Sheets data.

Handles Russian-specific number formatting:
- Decimal separator: comma (,)
- Thousand separator: space ( )
- Currency symbol: р.
- Boolean values: "Да"/"Нет"
- Date format: DD.MM.YYYY

Example:
    >>> parse_russian_decimal("1 000,25")
    Decimal('1000.25')

    >>> parse_russian_percentage("3,85%")
    Decimal('3.85')

    >>> parse_russian_currency("р.7 000 000,00")
    Decimal('7000000.00')

    >>> parse_boolean("Да")
    True

    >>> parse_date("23.06.2025")
    datetime.date(2025, 6, 23)
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional


def parse_russian_decimal(value: Optional[str]) -> Optional[Decimal]:
    """
    Parse a Russian-formatted decimal number to Python Decimal.

    Russian format uses comma as decimal separator and space as thousand separator.

    Args:
        value: Russian-formatted number string (e.g., "1 000,25") or None/empty

    Returns:
        Decimal object or None if input is empty/None

    Raises:
        ValueError: If value cannot be parsed as a valid decimal

    Examples:
        >>> parse_russian_decimal("1 000,25")
        Decimal('1000.25')
        >>> parse_russian_decimal("2,5")
        Decimal('2.5')
        >>> parse_russian_decimal("")
        None
        >>> parse_russian_decimal(None)
        None
    """
    if not value or not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    try:
        # Remove spaces (thousand separators)
        # Handle both regular spaces and non-breaking spaces (U+00A0)
        normalized = value.replace(" ", "").replace("\xa0", "").replace(",", ".")
        return Decimal(normalized)
    except (ValueError, InvalidOperation) as e:
        raise ValueError(f"Cannot parse Russian decimal '{value}': {e}") from e


def parse_russian_percentage(value: Optional[str]) -> Optional[Decimal]:
    """
    Parse a Russian-formatted percentage to Python Decimal.

    Handles Russian format with comma decimal separator and % suffix.

    Args:
        value: Russian-formatted percentage string (e.g., "3,85%") or None/empty

    Returns:
        Decimal object (e.g., Decimal('3.85')) or None if input is empty

    Raises:
        ValueError: If value cannot be parsed as a valid percentage

    Examples:
        >>> parse_russian_percentage("3,85%")
        Decimal('3.85')
        >>> parse_russian_percentage("1,54%")
        Decimal('1.54')
        >>> parse_russian_percentage("")
        None
    """
    if not value or not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    try:
        # Remove % suffix
        value = value.rstrip("%").strip()
        # Parse as decimal
        return parse_russian_decimal(value)
    except ValueError as e:
        raise ValueError(f"Cannot parse Russian percentage '{value}': {e}") from e


def parse_russian_currency(value: Optional[str]) -> Optional[Decimal]:
    """
    Parse a Russian-formatted currency value to Python Decimal.

    Handles Russian format with рuble symbol (р.), comma decimal separator,
    and space thousand separators.

    Args:
        value: Russian-formatted currency string (e.g., "р.7 000 000,00") or None/empty

    Returns:
        Decimal object (e.g., Decimal('7000000.00')) or None if input is empty

    Raises:
        ValueError: If value cannot be parsed as a valid number

    Examples:
        >>> parse_russian_currency("р.7 000 000,00")
        Decimal('7000000.00')
        >>> parse_russian_currency("р.5 000 000,00")
        Decimal('5000000.00')
        >>> parse_russian_currency("")
        None
    """
    if not value or not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    try:
        # Remove ruble symbol (р., р, руб, etc.)
        value = value.replace("р.", "").replace("р", "").replace("руб", "").strip()
        # Parse as decimal
        return parse_russian_decimal(value)
    except ValueError as e:
        raise ValueError(f"Cannot parse Russian currency '{value}': {e}") from e


def parse_boolean(value: Optional[str]) -> bool:
    """
    Parse a Russian boolean value ("Да"/"Нет") to Python bool.

    Args:
        value: Russian boolean string ("Да" for True, anything else for False) or None/empty

    Returns:
        True if value is "Да", False otherwise

    Examples:
        >>> parse_boolean("Да")
        True
        >>> parse_boolean("Нет")
        False
        >>> parse_boolean("")
        False
        >>> parse_boolean(None)
        False
    """
    if not value or not isinstance(value, str):
        return False

    return value.strip().lower() == "да"


def parse_date(value: Optional[str]) -> Optional[date]:
    """Parse a Russian-formatted date string to Python date object.

    Handles format: "DD.MM.YYYY" (e.g., "23.06.2025")

    Args:
        value: Date string in format "DD.MM.YYYY" or None/empty

    Returns:
        datetime.date object or None if input is empty

    Raises:
        ValueError: If date format is invalid

    Examples:
        >>> parse_date("23.06.2025")
        datetime.date(2025, 6, 23)
        >>> parse_date("01.01.2024")
        datetime.date(2024, 1, 1)
        >>> parse_date("")
        None
        >>> parse_date(None)
        None
    """
    if not value or not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError as e:
        raise ValueError(f"Cannot parse date '{value}' (expected DD.MM.YYYY): {e}") from e
