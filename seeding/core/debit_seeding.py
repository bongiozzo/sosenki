"""Debit transaction parsing and creation utilities for database seeding.

This module handles debit row parsing from Google Sheets.
Creation is delegated to transaction_seeding.create_debit_transactions()
"""

import logging
from typing import Dict, List, Optional

from seeding.config.seeding_config import SeedingConfig
from seeding.core.errors import DataValidationError
from seeding.core.parsers import parse_date, parse_russian_currency


def parse_debit_row(  # noqa: C901
    row_dict: Dict[str, str], account_column: str = None, config: SeedingConfig = None
) -> Optional[Dict]:
    """
    Parse a row from debit sheet into debit attributes.

    Uses three-phase approach:
    Phase 1: Extract fields from row using column mappings
    Phase 2: Validate required fields (amount and date)
    Phase 3: Parse and convert field values

    Args:
        row_dict: Dictionary mapping column names to cell values
        account_column: Optional column name that contains account name (e.g., 'Счет')
        config: Optional SeedingConfig instance (loads if not provided)

    Returns:
        Dict with debit attributes (including account_name if account_column specified)
        or None if row should be skipped (empty amount)

    Raises:
        DataValidationError: If required fields are invalid
    """
    logger = logging.getLogger("sosenki.seeding.debits")

    # Load configuration
    if config is None:
        config = SeedingConfig.load()
    parsing_rules = config.get_debit_parsing_rules()

    # PHASE 1: Extract field column names
    owner_name_column = parsing_rules.get("owner_name_column", "Собственник")
    amount_column = parsing_rules.get("amount_column", "Сумма")
    date_column = parsing_rules.get("date_column", "Дата")
    comment_column = parsing_rules.get("comment_column", "Комментарий")

    owner_name = row_dict.get(owner_name_column, "").strip()
    amount_str = row_dict.get(amount_column, "").strip()
    date_str = row_dict.get(date_column, "").strip()
    comment = row_dict.get(comment_column, "").strip() or None

    # Check for Skip marker
    if owner_name == "Skip":
        logger.info("Skipping record")
        raise DataValidationError("Row marked as Skip")

    # PHASE 2: Validate required fields
    if not owner_name:
        logger.debug("Skipping debit row: empty owner name")
        raise DataValidationError("Empty owner name")

    if not amount_str:
        logger.debug(f"Skipping debit row for {owner_name}: empty amount")
        raise DataValidationError("Empty amount")

    if not date_str:
        logger.debug(f"Skipping debit row for {owner_name}: empty date")
        raise DataValidationError("Empty payment date")

    # Extract account name from row if column specified
    account_name = None
    if account_column:
        account_name = row_dict.get(account_column, "").strip() or None

    # Use default account from config if not specified in row
    if not account_name:
        account_name = config.get_debit_default_account()

    # PHASE 3: Parse and convert field values
    try:
        amount = parse_russian_currency(amount_str)
        if amount is None or amount <= 0:
            raise ValueError("Amount must be positive")

        debit_date = parse_date(date_str)
        if debit_date is None:
            raise ValueError("Invalid debit date")
    except (ValueError, DataValidationError) as e:
        raise DataValidationError(f"Failed to parse debit for {owner_name}: {e}") from e

    return {
        "owner_name": owner_name,
        "amount": amount,
        "debit_date": debit_date,
        "comment": comment,
        "account_name": account_name,
    }


def parse_debit_range_with_service_period(
    debit_dicts: List[Dict],
    range_name: str,
    config: SeedingConfig = None,
) -> tuple[List[Dict], Dict]:
    """
    Enrich debit dicts with service period information based on range name.

    Args:
        debit_dicts: List of parsed debit dicts from parse_debit_row()
        range_name: Google Sheets range name (e.g., 'Contrib2425', 'Contrib25_1')
        config: Optional SeedingConfig instance (loads if not provided)

    Returns:
        Tuple of (enriched_debit_dicts, service_period_dict)

    Raises:
        DataValidationError: If range name is not mapped to service period
    """
    from seeding.core.seeding_utils import parse_range_with_service_period

    return parse_range_with_service_period(
        debit_dicts, range_name, "sosenki.seeding.debits", config
    )
