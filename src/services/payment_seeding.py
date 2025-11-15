"""Payment parsing and creation utilities for database seeding."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.config.seeding_config import SeedingConfig
from src.models.account import Account
from src.models.payment import Payment
from src.models.user import User
from src.services.errors import DataValidationError
from src.services.parsers import parse_russian_currency


def parse_date(value: Optional[str]) -> Optional[datetime]:
    """
    Parse a Russian-formatted date string to Python date object.

    Handles format: "DD.MM.YYYY" (e.g., "23.06.2025")

    Args:
        value: Date string in format "DD.MM.YYYY" or None/empty

    Returns:
        datetime.date object or None if input is empty

    Raises:
        ValueError: If date format is invalid
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


def parse_payment_row(row_dict: Dict[str, str], account_column: str = None) -> Optional[Dict]:
    """
    Parse a row from payment sheet into Payment attributes.

    Uses three-phase approach:
    Phase 1: Extract fields from row using column mappings
    Phase 2: Validate required fields (amount and date)
    Phase 3: Parse and convert field values

    Args:
        row_dict: Dictionary mapping column names to cell values
        account_column: Optional column name that contains account name (e.g., 'Счет')

    Returns:
        Dict with Payment attributes (including account_name if account_column specified)
        or None if row should be skipped (empty amount)

    Raises:
        DataValidationError: If required fields are invalid
    """
    logger = logging.getLogger("sostenki.seeding.payments")

    # Load configuration
    config = SeedingConfig.load()
    parsing_rules = config.get_payment_parsing_rules()

    # PHASE 1: Extract field column names
    owner_name_column = parsing_rules.get("owner_name_column", "Собственник")
    amount_column = parsing_rules.get("amount_column", "Сумма")
    date_column = parsing_rules.get("date_column", "Дата")
    comment_column = parsing_rules.get("comment_column", "Комментарий")

    owner_name = row_dict.get(owner_name_column, "").strip()
    amount_str = row_dict.get(amount_column, "").strip()
    date_str = row_dict.get(date_column, "").strip()
    comment = row_dict.get(comment_column, "").strip() or None

    # PHASE 2: Validate required fields
    if not owner_name:
        logger.debug("Skipping payment row: empty owner name")
        raise DataValidationError("Empty owner name")

    if not amount_str:
        logger.debug(f"Skipping payment row for {owner_name}: empty amount")
        raise DataValidationError("Empty amount")

    if not date_str:
        logger.debug(f"Skipping payment row for {owner_name}: empty date")
        raise DataValidationError("Empty payment date")

    # Extract account name from row if column specified
    account_name = None
    if account_column:
        account_name = row_dict.get(account_column, "").strip() or None

    # PHASE 3: Parse and convert field values
    try:
        amount = parse_russian_currency(amount_str)
        if amount is None or amount <= 0:
            raise ValueError("Amount must be positive")

        payment_date = parse_date(date_str)
        if payment_date is None:
            raise ValueError("Invalid payment date")
    except (ValueError, DataValidationError) as e:
        raise DataValidationError(f"Failed to parse payment for {owner_name}: {e}") from e

    return {
        "owner_name": owner_name,
        "amount": amount,
        "payment_date": payment_date,
        "comment": comment,
        "account_name": account_name,
    }


def get_or_create_account(session: Session, name: str) -> Account:
    """
    Get existing account by name or create new account.

    Args:
        session: SQLAlchemy session
        name: Account name

    Returns:
        Account instance (existing or newly created)

    Raises:
        DataValidationError: On operation failure
    """
    logger = logging.getLogger("sostenki.seeding.payments")

    try:
        # Query for existing account by name
        account = session.query(Account).filter(Account.name == name).first()

        if account:
            return account

        # Create new account
        account = Account(name=name)
        session.add(account)
        session.flush()  # Get ID without commit

        logger.info(f"Created new account: {name}")
        return account

    except Exception as e:
        raise DataValidationError(f"Failed to get or create account '{name}': {e}") from e


def create_payments(
    session: Session,
    payment_dicts: List[Dict],
    account: Account = None,
    owner_map: Dict[str, User] = None,
    default_account_name: str = None,
) -> int:
    """
    Create payment records in database.

    Args:
        session: SQLAlchemy session
        payment_dicts: List of payment attribute dicts
        account: Account instance for all payments
        owner_map: Dict mapping owner names to User instances

    Returns:
        Number of payments created

    Raises:
        DataValidationError: If payment creation fails
    """
    logger = logging.getLogger("sostenki.seeding.payments")

    try:
        created_count = 0

        for payment_dict in payment_dicts:
            owner_name = payment_dict.pop("owner_name")
            owner = owner_map.get(owner_name) if owner_map else None

            if not owner:
                logger.warning(f"Owner not found: {owner_name}, skipping payment")
                continue

            # Extract account for this payment
            payment_account_name = payment_dict.pop("account_name", None)
            if payment_account_name:
                payment_account = get_or_create_account(session, payment_account_name)
            elif account:
                payment_account = account
            elif default_account_name:
                payment_account = get_or_create_account(session, default_account_name)
            else:
                raise DataValidationError("No account specified and no default account configured")

            payment = Payment(
                owner_id=owner.id,
                account_id=payment_account.id,
                **payment_dict,
            )
            session.add(payment)
            logger.info(
                f"Created payment: {owner_name} {payment_dict['amount']} {payment_dict['payment_date']}"
            )
            created_count += 1

        logger.info(f"Created {created_count} payment records")
        return created_count

    except Exception as e:
        raise DataValidationError(f"Failed to create payments: {e}") from e
