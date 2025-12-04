"""Simple localization module for SOSenki.

Loads Russian translations from translations.json once at import time.
Provides a single t(key, **kwargs) function for translation lookup with semantic categories.

Usage:
    from src.services.localizer import t

    # Simple lookup
    message = t("labels.welcome")

    # With placeholder substitution
    message = t("errors.group_chat_error", bot_name="SOSenkiBot")
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Load translations once at import time
_TRANSLATIONS_PATH = Path(__file__).parent.parent / "static" / "mini_app" / "translations.json"
_TRANSLATIONS: dict[str, Any] = {}

try:
    with open(_TRANSLATIONS_PATH, encoding="utf-8") as f:
        _TRANSLATIONS = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    logger.error("Failed to load translations from %s: %s", _TRANSLATIONS_PATH, e)


def t(key: str, **kwargs: Any) -> str:
    """Get translation for a key with optional placeholder substitution.

    Args:
        key: Dot-notation key (e.g., "labels.welcome", "errors.group_chat_error")
        **kwargs: Placeholder values for string formatting

    Returns:
        Translated string with placeholders replaced, or the key itself if not found.

    Examples:
        >>> t("labels.welcome")
        "Добро пожаловать в SOSenki! 🏠"

        >>> t("errors.group_chat_error", bot_name="SOSenkiBot")
        "❌ Запросы можно отправлять только в личные сообщения..."
    """
    parts = key.split(".")
    value: Any = _TRANSLATIONS

    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            logger.warning("Translation key not found: %s", key)
            return key

    if not isinstance(value, str):
        logger.warning("Translation value is not a string for key: %s", key)
        return key

    if kwargs:
        try:
            return value.format(**kwargs)
        except KeyError as e:
            logger.warning("Missing placeholder %s for key: %s", e, key)
            return value

    return value


__all__ = ["t"]
