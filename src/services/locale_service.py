"""Centralized locale service for currency, dates, and number formatting.

Single source of truth for all locale-related operations.
Uses babel library with system timezone auto-detection.

Configuration:
    LOCALE env var (default: ru_RU) - determines currency, number/date formatting

Example:
    >>> from src.services.locale_service import format_amount, format_local_datetime
    >>> format_amount(1234.56)
    '1 234,56 ₽'
    >>> format_local_datetime(datetime.now(UTC))
    '8 дек. 2025 г., 12:30:00'
"""

import logging
import os
from datetime import datetime, tzinfo
from decimal import Decimal

from babel import Locale, UnknownLocaleError
from babel.dates import (
    LOCALTZ,
    get_timezone_name,
)
from babel.dates import (
    format_datetime as babel_format_datetime,
)
from babel.numbers import (
    format_currency as babel_format_currency,
)
from babel.numbers import (
    format_decimal as babel_format_decimal,
)
from babel.numbers import (
    get_currency_symbol as babel_get_currency_symbol,
)
from babel.numbers import (
    get_territory_currencies,
)
from babel.numbers import (
    parse_decimal as babel_parse_decimal,
)

logger = logging.getLogger(__name__)

# Default locale if LOCALE env var is invalid or missing
DEFAULT_LOCALE = "ru_RU"


def _get_locale() -> str:
    """Get locale from environment with validation and fallback.

    Returns:
        Valid locale string (e.g., 'ru_RU')
    """
    locale_str = os.getenv("LOCALE", DEFAULT_LOCALE)
    try:
        # Validate locale exists in babel
        Locale.parse(locale_str)
        return locale_str
    except (UnknownLocaleError, ValueError) as e:
        logger.warning(f"Invalid LOCALE '{locale_str}': {e}. Falling back to '{DEFAULT_LOCALE}'")
        return DEFAULT_LOCALE


def _get_currency_from_locale(locale_str: str) -> str:
    """Derive currency code from locale territory.

    Args:
        locale_str: Locale string (e.g., 'ru_RU')

    Returns:
        Currency code (e.g., 'RUB')
    """
    try:
        locale = Locale.parse(locale_str)
        territory = locale.territory
        if territory:
            currencies = get_territory_currencies(territory)
            if currencies:
                return currencies[0]
    except (UnknownLocaleError, ValueError) as e:
        logger.warning(f"Could not derive currency from locale '{locale_str}': {e}")

    # Fallback to RUB for Russian locale
    return "RUB"


# Module-level constants (computed once at import)
LOCALE = _get_locale()
CURRENCY = _get_currency_from_locale(LOCALE)


def get_system_timezone() -> tzinfo:
    """Get system timezone via babel auto-detection.

    Returns:
        tzinfo object representing local system timezone
    """
    return LOCALTZ


def get_timezone_display_name() -> str:
    """Get human-readable timezone name for current locale.

    Returns:
        Localized timezone name (e.g., 'Самарское время')
    """
    return get_timezone_name(LOCALTZ, locale=LOCALE)


def get_currency_code() -> str:
    """Get currency code derived from locale.

    Returns:
        ISO 4217 currency code (e.g., 'RUB')
    """
    return CURRENCY


def get_currency_symbol() -> str:
    """Get currency symbol for current locale.

    Returns:
        Currency symbol (e.g., '₽')
    """
    return babel_get_currency_symbol(CURRENCY, locale=LOCALE)


def format_amount(amount: float | Decimal, include_symbol: bool = True) -> str:
    """Format monetary amount according to locale.

    Args:
        amount: Numeric amount to format
        include_symbol: Whether to include currency symbol (default True)

    Returns:
        Formatted currency string (e.g., '1 234,56 ₽')

    Example:
        >>> format_amount(1234.56)
        '1 234,56 ₽'
        >>> format_amount(1234.56, include_symbol=False)
        '1 234,56'
    """
    if include_symbol:
        return babel_format_currency(float(amount), CURRENCY, locale=LOCALE)
    else:
        return babel_format_decimal(float(amount), locale=LOCALE)


def format_local_datetime(
    dt: datetime, format: str = "medium", include_timezone: bool = False
) -> str:
    """Format datetime in local timezone according to locale.

    Args:
        dt: Datetime object (timezone-aware recommended)
        format: One of 'full', 'long', 'medium', 'short' or custom pattern
        include_timezone: Whether to include timezone in output

    Returns:
        Formatted datetime string in local timezone

    Example:
        >>> from datetime import datetime, UTC
        >>> format_local_datetime(datetime.now(UTC))
        '8 дек. 2025 г., 12:30:00'
    """
    if include_timezone:
        format = "long"
    return babel_format_datetime(dt, format=format, tzinfo=LOCALTZ, locale=LOCALE)


def parse_decimal(value: str) -> Decimal:
    """Parse locale-formatted decimal string to Decimal.

    Uses babel to handle locale-specific separators.

    Args:
        value: Locale-formatted number string (e.g., '1 234,56' for ru_RU)

    Returns:
        Decimal object

    Raises:
        NumberFormatError: If value cannot be parsed

    Example:
        >>> parse_decimal('1 234,56')
        Decimal('1234.56')
    """
    return babel_parse_decimal(value.strip(), locale=LOCALE)


def get_locale_info() -> dict:
    """Get current locale configuration for debugging/display.

    Returns:
        Dict with locale, currency, timezone info
    """
    return {
        "locale": LOCALE,
        "currency_code": CURRENCY,
        "currency_symbol": get_currency_symbol(),
        "timezone": str(LOCALTZ),
        "timezone_name": get_timezone_display_name(),
    }


__all__ = [
    "LOCALE",
    "CURRENCY",
    "get_system_timezone",
    "get_timezone_display_name",
    "get_currency_code",
    "get_currency_symbol",
    "format_amount",
    "format_local_datetime",
    "parse_decimal",
    "get_locale_info",
]
