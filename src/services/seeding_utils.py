"""User parsing and creation utilities for database seeding.

Handles synchronous user role assignment logic, lookup, and creation
from Google Sheets data. Separate from the async UserService used by bot.
"""

import logging
from typing import Dict, Optional

from sqlalchemy.orm import Session

from src.config.seeding_config import SeedingConfig
from src.models.user import User
from src.services.errors import DataValidationError


def parse_user_row(row_dict: Dict[str, str]) -> Optional[Dict]:
    """
    Parse a row from named range into User attributes.

    Uses three-phase approach:
    Phase 1: Extract fields from row using column mappings from config
    Phase 2: Apply default attributes
    Phase 3: Apply transformations (special rules)

    Args:
        row_dict: Dictionary mapping column names to cell values

    Returns:
        Dict with User attributes or None if row should be skipped

    Raises:
        DataValidationError: If owner name is empty/whitespace
    """
    logger = logging.getLogger("sosenki.seeding.parsers")

    # Load configuration
    config = SeedingConfig.load()

    # PHASE 1: Extract fields from row using configured column mappings
    parsing_rules = config.get_user_parsing_rules()
    name_column = parsing_rules.get("name_column")
    stakeholder_column = parsing_rules.get("stakeholder_column")

    owner_name = row_dict.get(name_column, "").strip()

    # Validation: empty owner name
    if not owner_name:
        logger.warning("Skipping row: empty owner name (%s column)", name_column)
        raise DataValidationError("Empty owner name")

    stakeholder_value = row_dict.get(stakeholder_column, "").strip()

    # PHASE 2: Apply default attributes
    user_dict = config.get_user_defaults().copy()
    user_dict["name"] = owner_name
    user_dict["is_stakeholder"] = bool(stakeholder_value)

    # PHASE 3: Apply transformations (special rules)
    special_rules = config.get_user_special_rule(owner_name)
    if special_rules:
        logger.info("Applying special rules for user: %s", owner_name)
        user_dict.update(special_rules)

    return user_dict


def get_or_create_user(session: Session, name: str, user_attrs: Optional[Dict] = None) -> User:
    """
    Get existing user by name or create new user with personal account.

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
    3. If not found: create new user with provided attributes or config defaults
    4. Auto-create personal Account for the user (account_type='user')
    5. Flush transaction (get ID without full commit)
    """
    logger = logging.getLogger("sosenki.seeding.users")

    try:
        # Query for existing user by name
        user = session.query(User).filter(User.name == name).first()

        if user:
            logger.info(f"Found existing user: {name}")
            return user

        # Create new user with provided attributes or config defaults
        if not user_attrs:
            config = SeedingConfig.load()
            user_attrs = config.get_user_defaults().copy()
            user_attrs["name"] = name

        user = User(**user_attrs)
        session.add(user)
        session.flush()  # Get the ID before full commit

        # Auto-create personal account for the user
        from src.models.account import Account, AccountType

        user_account = Account(
            name=name,
            account_type=AccountType.USER,
            user_id=user.id,
        )
        session.add(user_account)
        session.flush()

        logger.info(
            f"Created new user: {name} "
            f"(investor={user.is_investor}, stakeholder={user.is_stakeholder})"
        )
        logger.info(f"Created personal account for user: {name}")
        return user

    except Exception as e:
        raise DataValidationError(f"Failed to get or create user '{name}': {e}") from e


def sheet_row_to_dict(row_values: list, header_names: list) -> Dict[str, str]:
    """
    Convert row values to dictionary using header names.

    Args:
        row_values: List of cell values in the row
        header_names: List of column header names

    Returns:
        Dictionary mapping header name to cell value

    Example:
        >>> row = ["1", "John", "Large"]
        >>> headers = ["ID", "Owner", "Size"]
        >>> sheet_row_to_dict(row, headers)
        {"ID": "1", "Owner": "John", "Size": "Large"}
    """
    result = {}
    for idx, header_name in enumerate(header_names):
        if idx < len(row_values):
            result[header_name] = row_values[idx]
        else:
            result[header_name] = ""

    return result
