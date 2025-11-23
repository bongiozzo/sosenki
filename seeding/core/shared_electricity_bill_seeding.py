"""
Shared electricity bill seeding utilities.
Handles parsing and creation of shared electricity bills from Google Sheets data.
"""

from decimal import Decimal
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from seeding.core.parsers import parse_russian_currency
from src.models import Bill, BillType, ServicePeriod, User


def parse_shared_electricity_bill_row(
    row_dict: Dict[str, Any],
    user_map: Dict[str, User],
    service_period: ServicePeriod,
    name_based_rules: Dict[str, Dict[str, float]] | None = None,
) -> List[Bill] | None:
    """
    Parse a single shared electricity bill row from Google Sheets.

    Handles split user names by:
    1. Checking if user name contains '/'
    2. Looking up coefficients in name_based_rules
    3. Splitting the amount proportionally among users
    4. Creating bills for each split user

    Args:
        row_dict: Dictionary with parsed row data containing 'user' and 'amount' keys
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

        # Validate required fields
        if not user_name or not amount_str:
            return None

        # Parse amount to Decimal using Russian currency parser (handles р. prefix)
        total_amount = parse_russian_currency(amount_str)
        if total_amount is None:
            return None

        # Extract optional comment
        comment = row_dict.get("comment", "").strip() or None

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
                proportional_amount = total_amount * Decimal(str(coefficient))

                bill = Bill(
                    service_period_id=service_period.id,
                    user_id=user.id,
                    bill_type=BillType.SHARED_ELECTRICITY,
                    bill_amount=proportional_amount,
                    comment=comment,
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
            bill_type=BillType.SHARED_ELECTRICITY,
            bill_amount=total_amount,
            comment=comment,
        )

        return [bill]

    except (KeyError, AttributeError):
        return None


def create_shared_electricity_bills(
    bills_data: List[Dict[str, Any]],
    user_map: Dict[str, User],
    service_period: ServicePeriod,
    session: Session,
    name_based_rules: Dict[str, Dict[str, float]] | None = None,
) -> int:
    """
    Create shared electricity bills in the database.

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
        bills = parse_shared_electricity_bill_row(
            bill_dict, user_map, service_period, name_based_rules
        )

        if bills:
            for bill in bills:
                try:
                    # Check for existing bill (unique constraint on service_period_id, user_id, bill_type)
                    existing = (
                        session.query(Bill)
                        .filter(
                            Bill.service_period_id == service_period.id,
                            Bill.user_id == bill.user_id,
                            Bill.bill_type == BillType.SHARED_ELECTRICITY,
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
