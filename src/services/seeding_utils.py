"""User parsing and creation utilities for database seeding.

Handles synchronous user role assignment logic, lookup, and creation
from Google Sheets data. Separate from the async UserService used by bot.
"""

import logging
from typing import Dict, Optional

from sqlalchemy.orm import Session

from src.models.user import User
from src.services.errors import DataValidationError


def parse_user_row(row_dict: Dict[str, str]) -> Optional[Dict]:
    """
    Parse a row from "Дома" sheet into User attributes.

    Args:
        row_dict: Dictionary mapping column names to cell values

    Returns:
        Dict with User attributes or None if row should be skipped

    Raises:
        DataValidationError: If owner name is empty/whitespace

    Parsing Rules:
    1. Extract owner name from "Фамилия" column
    2. If empty/whitespace-only: skip row, log WARNING
    3. Assign role flags: is_investor=True, is_owner=True
    4. is_administrator=True only for "Поляков"
    5. is_stakeholder=True if "Доля в Терра-М" column has value
    """
    logger = logging.getLogger("sostenki.seeding.parsers")

    # Extract owner name from "Фамилия" column
    owner_name = row_dict.get("Фамилия", "").strip()

    # Validation: empty owner name
    if not owner_name:
        logger.warning("Skipping row: empty owner name (Фамилия column)")
        raise DataValidationError("Empty owner name")

    # Determine stakeholder status from "Доля в Терра-М" column
    stakeholder_value = row_dict.get("Доля в Терра-М", "").strip()
    is_stakeholder = bool(stakeholder_value)

    # Determine administrator status (special case for Поляков)
    is_administrator = owner_name == "Поляков"

    return {
        "name": owner_name,
        "is_investor": True,  # Default for all seeded users
        "is_owner": True,  # Default for all seeded users
        "is_administrator": is_administrator,
        "is_stakeholder": is_stakeholder,
        "is_active": True,
    }


def get_or_create_user(
    session: Session, name: str, user_attrs: Optional[Dict] = None
) -> User:
    """
    Get existing user by name or create new user.

    Args:
        session: SQLAlchemy session
        name: User name (unique identifier)
        user_attrs: Dict of attributes for new user (if creation needed)

    Returns:
        User instance (existing or newly created)

    Raises:
        DataValidationError: If user lookup fails

    Logic:
    1. Query user by name (case-sensitive, exact match)
    2. If found: return existing user
    3. If not found: create new user with provided attributes
    4. Flush transaction (get ID without full commit)
    """
    logger = logging.getLogger("sostenki.seeding.users")

    try:
        # Query for existing user by name
        user = session.query(User).filter(User.name == name).first()

        if user:
            logger.info(f"Found existing user: {name}")
            return user

        # Create new user
        if not user_attrs:
            user_attrs = {
                "name": name,
                "is_investor": True,
                "is_owner": True,
                "is_administrator": False,
                "is_stakeholder": False,
                "is_active": True,
            }

        user = User(**user_attrs)
        session.add(user)
        session.flush()  # Get the ID before full commit

        logger.info(
            f"Created new user: {name} "
            f"(investor={user.is_investor}, stakeholder={user.is_stakeholder})"
        )
        return user

    except Exception as e:
        raise DataValidationError(
            f"Failed to get or create user '{name}': {e}"
        ) from e


def sheet_row_to_dict(
    row_values: list, header_names: list
) -> Dict[str, str]:
    """
    Convert sheet row (list of values) to dictionary using header names.

    Args:
        row_values: List of cell values in the row
        header_names: List of column header names

    Returns:
        Dictionary mapping header name to cell value

    Example:
        >>> row = ["1", "Иванчик/Радионов", "Большой"]
        >>> headers = ["Дом", "Фамилия", "Размер"]
        >>> sheet_row_to_dict(row, headers)
        {"Дом": "1", "Фамилия": "Иванчик/Радионов", "Размер": "Большой"}
    """
    result = {}
    for idx, header_name in enumerate(header_names):
        if idx < len(row_values):
            result[header_name] = row_values[idx]
        else:
            result[header_name] = ""

    return result
