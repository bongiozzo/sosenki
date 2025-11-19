"""Credit transaction parsing and creation utilities for database seeding.

This module handles credit/expense row parsing from Google Sheets.
Creation is delegated to transaction_seeding.create_credit_transactions()
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from src.config.seeding_config import SeedingConfig
from src.services.errors import DataValidationError
from src.services.parsers import parse_russian_currency


def parse_date(value: Optional[str]) -> Optional[datetime]:
    """Parse a Russian-formatted date string to Python date object.

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


def parse_credit_row(row_dict: Dict[str, str]) -> Optional[Dict]:  # noqa: C901
    """Parse a row from credits sheet into credit attributes.

    Uses three-phase approach:
    Phase 1: Extract fields from row using column mappings
    Phase 2: Validate required fields (payer name, amount, date)
    Phase 3: Parse and convert field values

    Args:
        row_dict: Dictionary mapping column names to cell values

    Returns:
        Dict with credit attributes (payer_name, expense_type, amount, debit_date, etc.)
        or None if row should be skipped

    Raises:
        DataValidationError: If required fields are invalid
    """
    logger = logging.getLogger("sosenki.seeding.credits")

    # Load configuration
    config = SeedingConfig.load()
    parsing_rules = config.get_credit_parsing_rules()

    # PHASE 1: Extract field column names from config
    payer_name_column = parsing_rules.get("name_column", "Кто")
    amount_column = parsing_rules.get("amount_column", "Сколько")
    date_column = parsing_rules.get("date_column", "Когда")
    expense_type_column = parsing_rules.get("type_column", "Тип")
    comment_column = parsing_rules.get("comment_column", "Сбор")

    payer_name = row_dict.get(payer_name_column, "").strip()
    amount_str = row_dict.get(amount_column, "").strip()
    date_str = row_dict.get(date_column, "").strip()
    expense_type_raw = row_dict.get(expense_type_column, "").strip() or "Other"
    comment = row_dict.get(comment_column, "").strip() or None

    # Check for Skip marker in payer_name
    if payer_name == "Skip":
        logger.info("Skipping record")
        raise DataValidationError("Row marked as Skip")

    # PHASE 2: Validate required fields
    if not payer_name:
        logger.debug("Skipping credit row: empty payer name")
        raise DataValidationError("Empty payer name")

    if not amount_str:
        logger.debug(f"Skipping credit row for {payer_name}: empty amount")
        raise DataValidationError("Empty amount")

    if not date_str:
        logger.debug(f"Skipping credit row for {payer_name}: empty date")
        raise DataValidationError("Empty debit date")

    # PHASE 3: Parse and convert field values
    try:
        amount = parse_russian_currency(amount_str)
        if amount is None or amount <= 0:
            raise ValueError("Amount must be positive")

        debit_date = parse_date(date_str)
        if debit_date is None:
            raise ValueError("Invalid debit date")
    except (ValueError, DataValidationError) as e:
        raise DataValidationError(f"Failed to parse credit for {payer_name}: {e}") from e

    # Parse expense_type_raw to extract budget_item and account_name
    # Format: "BUDGET_ITEM ACCOUNT_NAME" or just "ACCOUNT_NAME"
    budget_item_name = None
    account_name = None

    expense_parts = expense_type_raw.split(maxsplit=1)
    if len(expense_parts) == 2:
        budget_item_name = expense_parts[0]
        account_name = expense_parts[1]
    elif len(expense_parts) == 1:
        # Single word = account name
        account_name = expense_parts[0]

    # Check for Skip marker in account_name
    if account_name == "Skip":
        logger.info("Skipping record")
        raise DataValidationError("Row marked as Skip")

    return {
        "payer_name": payer_name,
        "expense_type": expense_type_raw,
        "amount": amount,
        "debit_date": debit_date,
        "description": comment,
        "budget_item_name": budget_item_name,
        "account_name": account_name,
    }


def parse_credit_range_with_service_period(
    credit_dicts: List[Dict],
    range_name: str,
    config: SeedingConfig = None,
) -> tuple[List[Dict], Dict]:
    """
    Enrich credit dicts with service period information based on range name.

    Args:
        credit_dicts: List of parsed credit dicts from parse_credit_row()
        range_name: Google Sheets range name (e.g., 'Credit2425', 'Credit25_1')
        config: Optional SeedingConfig instance (loads if not provided)

    Returns:
        Tuple of (enriched_credit_dicts, service_period_dict)

    Raises:
        DataValidationError: If range name is not mapped to service period
    """
    if config is None:
        config = SeedingConfig.load()

    logger = logging.getLogger("sosenki.seeding.credits")

    service_periods = config.get_service_periods()
    if range_name not in service_periods:
        raise DataValidationError(
            f"Range '{range_name}' not mapped to service period in config. "
            f"Available: {list(service_periods.keys())}"
        )

    period_info = service_periods[range_name]
    logger.info(f"Range '{range_name}' mapped to period '{period_info['name']}'")

    return credit_dicts, period_info
