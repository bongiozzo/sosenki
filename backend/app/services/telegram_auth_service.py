"""Telegram authentication service: initData verification and user management."""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs, unquote

from backend.app.api.errors import InvalidInitDataError
from backend.app.logging import logger


def verify_initdata(init_data: str, bot_token: str, max_age_seconds: int = 120) -> dict:
    """
    Verify Telegram Mini App initData signature using HMAC-SHA256.

    Follows Telegram's Web App authentication protocol:
    https://core.telegram.org/bots/webapps#validating-data-received-from-the-web-app

    Args:
        init_data: URL-encoded string from Telegram WebApp
        bot_token: Telegram bot token (for HMAC secret derivation)
        max_age_seconds: Maximum age of auth_date in seconds

    Returns:
        Dict with extracted user data if valid (telegram_id, auth_date, etc.)

    Raises:
        InvalidInitDataError: If signature verification or timestamp validation fails
    """
    try:
        # Parse query string while preserving percent-encoding for check_string
        parsed = parse_qs(init_data, keep_blank_values=True)

        # Extract hash (it's in a list from parse_qs)
        hash_value = parsed.get("hash", [None])[0]
        if not hash_value:
            logger.warning("initData missing hash field")
            raise InvalidInitDataError("Missing hash field")

        # Extract auth_date
        auth_date_str = parsed.get("auth_date", [None])[0]
        if not auth_date_str:
            logger.warning("initData missing auth_date field")
            raise InvalidInitDataError("Missing auth_date field")

        try:
            auth_date = int(auth_date_str)
        except ValueError:
            logger.warning(f"initData invalid auth_date format: {auth_date_str}")
            raise InvalidInitDataError("Invalid auth_date format")

        # Check timestamp freshness
        current_time = int(time.time())
        if current_time - auth_date > max_age_seconds:
            logger.warning(
                f"initData expired: age={current_time - auth_date}s, max={max_age_seconds}s"
            )
            raise InvalidInitDataError("initData expired")

        # Build check string from raw query parameters (preserving percent-encoding)
        # Split by & and sort by key
        check_string_parts = []
        for pair in init_data.split("&"):
            key, _, value = pair.partition("=")
            if key != "hash" and key and value:
                check_string_parts.append(pair)

        check_string_parts.sort()
        check_string = "\n".join(check_string_parts)

        # Compute HMAC-SHA256
        secret_key = hmac.new(
            b"WebAppData", msg=bot_token.encode(), digestmod=hashlib.sha256
        ).digest()
        computed_hash = hmac.new(
            secret_key, msg=check_string.encode(), digestmod=hashlib.sha256
        ).hexdigest()

        # Constant-time comparison
        if not hmac.compare_digest(computed_hash, hash_value):
            logger.warning("initData signature verification failed")
            raise InvalidInitDataError("Invalid signature")

        # Extract user data
        user_data_str = parsed.get("user", [None])[0]
        if not user_data_str:
            logger.warning("initData missing user field")
            raise InvalidInitDataError("Missing user field")

        user_data = json.loads(unquote(user_data_str))
        telegram_id = user_data.get("id")
        if not telegram_id:
            logger.warning("initData user missing id field")
            raise InvalidInitDataError("Missing telegram user id")

        logger.info(f"initData verified for telegram_id={telegram_id}")
        return {
            "telegram_id": telegram_id,
            "auth_date": auth_date,
            "user": user_data,
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse initData JSON: {e}")
        raise InvalidInitDataError("Invalid user data JSON")
    except Exception as e:
        if isinstance(e, InvalidInitDataError):
            raise
        logger.error(f"Unexpected error in verify_initdata: {e}")
        raise InvalidInitDataError("Verification failed")


def get_or_create_user(telegram_id: int, init_data_dict: dict) -> tuple[bool, dict]:
    """
    Get or create SOSenkiUser by telegram_id.

    ## Implementation TODO
    - Query database for SOSenkiUser with matching telegram_id
    - If user exists: return (linked=True, user_object)
    - If not found: create TelegramUserCandidate (pending admin approval)
      - Store telegram_id, user_data from initData
      - Return (linked=False, candidate_request_form)

    ## Arguments
    - telegram_id: Verified Telegram user ID from initData
    - init_data_dict: Parsed user data from verify_initdata

    ## Returns
    - Tuple: (is_linked: bool, data_dict: dict)
      - If linked: (True, {"user_id": ..., "role": ..., ...})
      - If unlinked: (False, {"form": {...}})

    ## Database Models Reference
    specs/001-seamless-telegram-auth/data-model.md
    """
    # TODO: implement database query/create logic
    # TODO: use SQLAlchemy models from backend/app/models/
    raise NotImplementedError("get_or_create_user not yet implemented")
