"""Bot handler authorization utilities.

Minimal wrapper around auth_service for Telegram bot handlers.
Handles async session management and error conversion.
"""

import logging

from src.models.user import User

logger = logging.getLogger(__name__)


async def verify_admin_authorization(telegram_id: int) -> User | None:
    """Verify user is authenticated admin.

    Performs unified authorization check:
    1. Lookup user from telegram_id
    2. Check is_active
    3. Check is_administrator role

    Args:
        telegram_id: Telegram ID to verify

    Returns:
        Verified User object (guaranteed is_active and is_administrator),
        or None if not authorized.
    """
    # Deferred imports to avoid circular dependency
    # (auth_service -> bot.config -> bot.handlers -> auth)
    from fastapi import HTTPException

    from src.services import AsyncSessionLocal
    from src.services.auth_service import get_authenticated_user

    async with AsyncSessionLocal() as async_session:
        try:
            # Chain of trust:
            # 1. Get user from telegram_id (ensures user exists and is_active)
            user = await get_authenticated_user(async_session, telegram_id)

            # 2. Check is_administrator role
            if not user.is_administrator:
                logger.warning(
                    f"Non-admin attempted admin operation: user_id={user.id}, telegram_id={telegram_id}"
                )
                return None

            return user

        except HTTPException as e:
            # get_authenticated_user raises HTTPException(401) if user not found or inactive
            logger.warning(f"Authorization failed for telegram_id={telegram_id}: {e.detail}")
            return None
        except Exception as e:
            logger.error(f"Error verifying admin authorization: {e}", exc_info=True)
            return None


__all__ = ["verify_admin_authorization"]
