"""Admin utility functions for retrieving admin user information."""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.user import User

logger = logging.getLogger(__name__)


def get_admin_telegram_id(db: Session) -> Optional[str]:
    """
    Get the admin's telegram ID from the database.

    Retrieves the first user with is_administrator=True.
    This replaces hardcoded ADMIN_TELEGRAM_ID environment variable.

    Args:
        db: SQLAlchemy session

    Returns:
        Admin's telegram_id as string, or None if no admin user found

    Raises:
        None - returns None gracefully if admin not found
    """
    try:
        admin_user = (
            db.execute(select(User).where(User.is_administrator.is_(True))).scalars().first()
        )

        if admin_user and admin_user.telegram_id:
            logger.debug("Retrieved admin telegram ID: %s", admin_user.telegram_id)
            return str(admin_user.telegram_id)

        logger.warning("No admin user found in database")
        return None

    except Exception as e:
        logger.error("Error retrieving admin telegram ID: %s", e, exc_info=True)
        return None


def get_admin_user(db: Session) -> Optional[User]:
    """
    Get the admin user from the database.

    Retrieves the first user with is_administrator=True.

    Args:
        db: SQLAlchemy session

    Returns:
        Admin User instance, or None if no admin user found

    Raises:
        None - returns None gracefully if admin not found
    """
    try:
        admin_user = (
            db.execute(select(User).where(User.is_administrator.is_(True))).scalars().first()
        )

        if admin_user:
            logger.debug("Retrieved admin user: %s", admin_user.name)
            return admin_user

        logger.warning("No admin user found in database")
        return None

    except Exception as e:
        logger.error("Error retrieving admin user: %s", e, exc_info=True)
        return None
