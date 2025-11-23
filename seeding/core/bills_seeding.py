"""
Bills seeding utilities.
Handles parsing and creation of regular bills (conservation, main, etc.) from Google Sheets data.
"""

from decimal import Decimal
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from seeding.core.parsers import parse_russian_currency
from src.models import Bill, BillType, ServicePeriod, User


def parse_bill_row(
    row_dict: Dict[str, Any],
    user_map: Dict[str, User],
    service_period: ServicePeriod,
    name_based_rules: Dict[str, Dict[str, float]] | None = None,
) -> List[Bill] | None:
    """
    Parse a single bill row from Google Sheets.

    Creates two separate lists:
    1. CONSERVATION bills: when 'conservation' column is not null/empty
    2. MAIN bills: when 'amount' column is not null/empty

    Both apply split rules if user name contains '/'.

    Args:
        row_dict: Dictionary with parsed row data containing 'user', 'amount', and optional 'conservation' keys
        user_map: Dictionary mapping user names to User objects
        service_period: ServicePeriod object for this bill
        name_based_rules: Dictionary mapping split names to user coefficients

    Returns:
        List of Bill objects if parsing successful, None if invalid data
        Skips records with '/' that have no matching rule
    """
    try:
        # Extract fields
        user_name = row_dict.get("user", "").strip()
        amount_str = row_dict.get("amount", "").strip()
        conservation_str = row_dict.get("conservation", "").strip()

        # Validate required field: user name
        if not user_name:
            return None

        bills = []

        # Create CONSERVATION bill if conservation column is not null/empty
        if conservation_str:
            conservation_amount = parse_russian_currency(conservation_str)
            if conservation_amount is not None:
                conservation_bills = _create_bills_for_user(
                    user_name,
                    conservation_amount,
                    BillType.CONSERVATION,
                    service_period,
                    user_map,
                    name_based_rules,
                )
                if conservation_bills:
                    bills.extend(conservation_bills)

        # Create MAIN bill if amount column is not null/empty
        if amount_str:
            main_amount = parse_russian_currency(amount_str)
            if main_amount is not None:
                main_bills = _create_bills_for_user(
                    user_name,
                    main_amount,
                    BillType.MAIN,
                    service_period,
                    user_map,
                    name_based_rules,
                )
                if main_bills:
                    bills.extend(main_bills)

        return bills if bills else None

    except (KeyError, AttributeError):
        return None


def _create_bills_for_user(
    user_name: str,
    amount: Decimal,
    bill_type: BillType,
    service_period: ServicePeriod,
    user_map: Dict[str, User],
    name_based_rules: Dict[str, Dict[str, float]] | None = None,
) -> List[Bill] | None:
    """
    Create bills for a user, handling split names.

    Args:
        user_name: User name (may contain '/')
        amount: Bill amount
        bill_type: Bill type (CONSERVATION or MAIN)
        service_period: ServicePeriod object
        user_map: Dictionary mapping user names to User objects
        name_based_rules: Dictionary mapping split names to user coefficients

    Returns:
        List of Bill objects, or None if user not found
    """
    # Handle split user names (with '/')
    if "/" in user_name:
        # Skip if no rules configured for this split
        if not name_based_rules or user_name not in name_based_rules:
            return None

        # Get coefficients for split users
        coefficients = name_based_rules.get(user_name, {})
        bills = []

        for split_user_name, coefficient in coefficients.items():
            # Find user
            user = user_map.get(split_user_name)
            if not user:
                continue

            # Calculate proportional amount
            proportional_amount = amount * Decimal(str(coefficient))

            bill = Bill(
                service_period_id=service_period.id,
                user_id=user.id,
                bill_type=bill_type,
                bill_amount=proportional_amount,
            )
            bills.append(bill)

        return bills if bills else None

    # Handle single user name (no '/')
    user = user_map.get(user_name)
    if not user:
        return None

    bill = Bill(
        service_period_id=service_period.id,
        user_id=user.id,
        bill_type=bill_type,
        bill_amount=amount,
    )

    return [bill]


def create_bills(
    bills_data: List[Dict[str, Any]],
    user_map: Dict[str, User],
    service_period: ServicePeriod,
    session: Session,
    name_based_rules: Dict[str, Dict[str, float]] | None = None,
) -> int:
    """
    Create bills in the database.

    Args:
        bills_data: List of bill dictionaries parsed from Google Sheets
        user_map: Dictionary mapping user names to User objects
        service_period: ServicePeriod object for these bills
        session: SQLAlchemy session
        name_based_rules: Dictionary mapping split names to user coefficients

    Returns:
        Number of bills created successfully
    """
    created_count = 0

    for bill_dict in bills_data:
        bills = parse_bill_row(bill_dict, user_map, service_period, name_based_rules)

        if bills:
            for bill in bills:
                try:
                    # Check for existing bill (unique constraint on service_period_id, user_id, bill_type)
                    existing = (
                        session.query(Bill)
                        .filter(
                            Bill.service_period_id == service_period.id,
                            Bill.user_id == bill.user_id,
                            Bill.bill_type == bill.bill_type,
                        )
                        .first()
                    )

                    if existing:
                        # Update existing bill
                        existing.bill_amount = bill.bill_amount
                        existing.comment = bill.comment
                    else:
                        # Create new bill
                        session.add(bill)

                    created_count += 1
                except Exception:
                    # Skip bills with errors
                    pass

    return created_count
