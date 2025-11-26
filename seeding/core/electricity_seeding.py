"""Electricity reading and bill parsing and creation utilities for database seeding."""

import logging
from datetime import date
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from seeding.config.seeding_config import SeedingConfig
from seeding.core.errors import DataValidationError
from seeding.core.parsers import parse_date, parse_russian_currency, parse_russian_decimal
from src.models.property import Property
from src.models.user import User


def parse_electricity_row(  # noqa: C901
    row_dict: Dict[str, str], config: SeedingConfig = None
) -> Optional[Dict]:
    """Parse a row from electricity sheet into electricity reading attributes.

    Extracts user name, property name, start reading, end reading.

    Args:
        row_dict: Dictionary mapping column names to cell values
        config: Optional SeedingConfig instance (loads if not provided)

    Returns:
        Dict with electricity reading attributes or None if row should be skipped

    Raises:
        DataValidationError: If required fields are invalid
    """
    if config is None:
        config = SeedingConfig.load()

    parsing_rules = config.get_electricity_parsing_rules()

    # Extract field column names
    user_column = parsing_rules.get("user", "Фамилия")
    property_column = parsing_rules.get("property", "Строение")
    start_column = parsing_rules.get("start_column", "От")
    end_column = parsing_rules.get("end_column", "До")
    amount_column = parsing_rules.get("amount_column", "Сумма")

    # Extract values from row
    user_name = row_dict.get(user_column, "").strip()
    property_name = row_dict.get(property_column, "").strip()
    start_reading_str = row_dict.get(start_column, "").strip()
    end_reading_str = row_dict.get(end_column, "").strip()
    amount_str = row_dict.get(amount_column, "").strip()

    # Validation
    if not user_name:
        raise DataValidationError("User name is required")
    if not property_name:
        raise DataValidationError("Property name is required")
    if not start_reading_str or not end_reading_str:
        raise DataValidationError("Start and end readings are required")
    if not amount_str:
        raise DataValidationError("Bill amount is required")

    # Parse readings and amount as decimals
    try:
        start_reading = parse_russian_decimal(start_reading_str)
        end_reading = parse_russian_decimal(end_reading_str)
        bill_amount = parse_russian_currency(amount_str)
    except ValueError as e:
        raise DataValidationError(f"Invalid numeric value: {e}") from e

    return {
        "user_name": user_name,
        "property_name": property_name,
        "start_reading": start_reading,
        "end_reading": end_reading,
        "bill_amount": bill_amount,
    }


def _find_property_by_name_or_type(
    session: Session, user_id: int, property_name: str
) -> Optional[Property]:
    """Find property by name (if numeric) or by type.

    Args:
        session: SQLAlchemy session
        user_id: Owner user ID
        property_name: Property name/type to search for

    Returns:
        Property object or None if not found
    """
    try:
        int(property_name)  # noqa: F841
        # If numeric, search by property_name
        return (
            session.query(Property)
            .filter(Property.owner_id == user_id, Property.property_name == property_name)
            .first()
        )
    except ValueError:
        # Not numeric, search by type
        return (
            session.query(Property)
            .filter(Property.owner_id == user_id, Property.type == property_name)
            .first()
        )


def _create_electricity_reading_if_not_exists(
    session: Session,
    user_id: int,
    property_id: int | None,
    reading_value: float,
    reading_date: date,
) -> bool:
    """Create electricity reading if it doesn't already exist.

    Returns True if created, False if already existed.
    """
    from src.models.electricity_reading import ElectricityReading

    query = session.query(ElectricityReading).filter(
        ElectricityReading.reading_date == reading_date,
        ElectricityReading.user_id == user_id,
    )
    if property_id:
        query = query.filter(ElectricityReading.property_id == property_id)

    if query.first():
        return False

    reading = ElectricityReading(
        user_id=user_id,
        property_id=property_id,
        reading_value=reading_value,
        reading_date=reading_date,
    )
    session.add(reading)
    session.flush()
    return True


def _create_electricity_bill_if_not_exists(
    session: Session,
    account_id: int,
    service_period_id: int,
    property_id: int | None,
    bill_amount: float,
    property_obj,
    property_name: str,
) -> bool:
    """Create electricity bill if it doesn't already exist.

    Returns True if created, False if already existed.
    """
    from src.models.bill import Bill, BillType

    existing = (
        session.query(Bill)
        .filter(
            Bill.service_period_id == service_period_id,
            Bill.account_id == account_id,
            Bill.property_id == property_id,
            Bill.bill_type == BillType.ELECTRICITY,
        )
        .first()
    )

    if existing:
        return False

    comment = property_name if not property_obj else None
    bill = Bill(
        service_period_id=service_period_id,
        account_id=account_id,
        property_id=property_id,
        bill_type=BillType.ELECTRICITY,
        bill_amount=bill_amount,
        comment=comment,
    )
    session.add(bill)
    session.flush()
    return True


def create_electricity_readings_and_bills(
    session: Session,
    reading_dicts: List[Dict],
    user_map: Dict[str, User],
    service_period_id: int,
    period_start_date: date,
    period_end_date: date,
) -> tuple[int, int]:
    """Create electricity reading and bill records from parsed data.

    Creates two readings per user/property (start/end dates) and one bill.
    """

    logger = logging.getLogger("sosenki.seeding.electricity")
    readings_created = 0
    bills_created = 0

    for reading_dict in reading_dicts:
        user_name = reading_dict["user_name"]
        property_name = reading_dict["property_name"]
        start_reading = reading_dict["start_reading"]
        end_reading = reading_dict["end_reading"]
        bill_amount = reading_dict["bill_amount"]

        user = user_map.get(user_name)
        if not user:
            logger.warning(f"User not found: {user_name}, skipping reading")
            continue

        property_obj = _find_property_by_name_or_type(session, user.id, property_name)
        property_id = property_obj.id if property_obj else None
        user_id = user.id

        try:
            # Create start reading
            if _create_electricity_reading_if_not_exists(
                session, user_id, property_id, start_reading, period_start_date
            ):
                readings_created += 1
                logger.debug(
                    f"Created electricity reading: {user_id}/{property_id} = {start_reading}"
                )

            # Create end reading
            if _create_electricity_reading_if_not_exists(
                session, user_id, property_id, end_reading, period_end_date
            ):
                readings_created += 1
                logger.debug(
                    f"Created electricity reading: {user_id}/{property_id} = {end_reading}"
                )

            # Create bill
            account_id = user.account.id if user.account else None
            if not account_id:
                logger.warning(f"User {user_name} has no account, skipping bill")
                continue

            if _create_electricity_bill_if_not_exists(
                session,
                account_id,
                service_period_id,
                property_id,
                bill_amount,
                property_obj,
                property_name,
            ):
                bills_created += 1
                logger.debug(
                    f"Created electricity bill: {account_id}/{property_id} = {bill_amount}"
                )

        except Exception as e:
            logger.error(f"Failed to create readings/bill for {property_name} ({user_name}): {e}")

    return readings_created, bills_created


__all__ = [
    "parse_electricity_row",
    "create_electricity_readings_and_bills",
    "parse_date",
]
