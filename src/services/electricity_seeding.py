"""Electricity reading and bill parsing and creation utilities for database seeding."""

import logging
from datetime import date
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.config.seeding_config import SeedingConfig
from src.models.property import Property
from src.models.user import User
from src.services.errors import DataValidationError
from src.services.parsers import parse_date, parse_russian_currency, parse_russian_decimal


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


def create_electricity_readings_and_bills(
    session: Session,
    reading_dicts: List[Dict],
    user_map: Dict[str, User],
    service_period_id: int,
    period_start_date: date,
    period_end_date: date,
) -> tuple[int, int]:
    """Create electricity reading and bill records from parsed data.

    Creates:
    - Two readings per user/property (start and end dates)
    - One bill per user/property for the service period

    Args:
        session: SQLAlchemy session
        reading_dicts: List of dicts from parse_electricity_row()
        user_map: User name -> User object mapping
        service_period_id: ID of the service period
        period_start_date: Start date for first reading
        period_end_date: End date for second reading

    Returns:
        Tuple of (readings_created, bills_created)
    """
    from src.models.electricity_bill import ElectricityBill
    from src.models.electricity_reading import ElectricityReading

    logger = logging.getLogger("sosenki.seeding.electricity")
    readings_created = 0
    bills_created = 0

    for reading_dict in reading_dicts:
        user_name = reading_dict["user_name"]
        property_name = reading_dict["property_name"]
        start_reading = reading_dict["start_reading"]
        end_reading = reading_dict["end_reading"]
        bill_amount = reading_dict["bill_amount"]

        # Find user
        user = user_map.get(user_name)
        if not user:
            logger.warning(f"User not found: {user_name}, skipping reading")
            continue

        # Find property by type and owner
        # The property_name in electricity data is actually the property type
        # (e.g., "Большой", "Малый", "Баня")
        property_obj = (
            session.query(Property)
            .filter(Property.owner_id == user.id, Property.type == property_name)
            .first()
        )

        try:
            # Determine if we have a property match
            property_id = property_obj.id if property_obj else None
            user_id = user.id if not property_id else None

            # Create first reading (start date with start reading value)
            # Check if reading already exists for this property/user and date
            query_start = session.query(ElectricityReading).filter(
                ElectricityReading.reading_date == period_start_date
            )
            if property_id:
                query_start = query_start.filter(ElectricityReading.property_id == property_id)
            else:
                query_start = query_start.filter(ElectricityReading.user_id == user_id)

            existing_start = query_start.first()

            if not existing_start:
                reading_start = ElectricityReading(
                    user_id=user_id,
                    property_id=property_id,
                    reading_value=start_reading,
                    reading_date=period_start_date,
                )
                session.add(reading_start)
                session.flush()  # Flush to make the reading queryable
                readings_created += 1
                logger.debug(
                    f"Created electricity reading: "
                    f"{'property=' + str(property_id) if property_id else 'user=' + str(user_id)} "
                    f"= {start_reading} on {period_start_date}"
                )
            else:
                logger.debug(
                    f"Skipped duplicate electricity reading: "
                    f"{'property=' + str(property_id) if property_id else 'user=' + str(user_id)} "
                    f"on {period_start_date}"
                )

            # Create second reading (end date with end reading value)
            # Check if reading already exists for this property/user and date
            query_end = session.query(ElectricityReading).filter(
                ElectricityReading.reading_date == period_end_date
            )
            if property_id:
                query_end = query_end.filter(ElectricityReading.property_id == property_id)
            else:
                query_end = query_end.filter(ElectricityReading.user_id == user_id)

            existing_end = query_end.first()

            if not existing_end:
                reading_end = ElectricityReading(
                    user_id=user_id,
                    property_id=property_id,
                    reading_value=end_reading,
                    reading_date=period_end_date,
                )
                session.add(reading_end)
                session.flush()  # Flush to make the reading queryable
                readings_created += 1
                logger.debug(
                    f"Created electricity reading: "
                    f"{'property=' + str(property_id) if property_id else 'user=' + str(user_id)} "
                    f"= {end_reading} on {period_end_date}"
                )
            else:
                logger.debug(
                    f"Skipped duplicate electricity reading: "
                    f"{'property=' + str(property_id) if property_id else 'user=' + str(user_id)} "
                    f"on {period_end_date}"
                )

            # Create bill with optional comment if property not found
            # Check if bill already exists for this service period, user/property combo
            existing_bill = (
                session.query(ElectricityBill)
                .filter(
                    ElectricityBill.service_period_id == service_period_id,
                    ElectricityBill.user_id == user_id,
                    ElectricityBill.property_id == property_id,
                )
                .first()
            )

            if not existing_bill:
                comment = None
                if not property_obj:
                    comment = property_name
                    logger.info(f"Bill created with user_id (property not found): {property_name}")

                bill = ElectricityBill(
                    service_period_id=service_period_id,
                    user_id=user_id,
                    property_id=property_id,
                    bill_amount=bill_amount,
                    comment=comment,
                )
                session.add(bill)
                session.flush()  # Flush to make bill queryable
                bills_created += 1
                logger.debug(
                    f"Created electricity bill: "
                    f"{'property=' + str(property_id) if property_id else 'user=' + str(user_id)} "
                    f"= {bill_amount} rubles"
                )
            else:
                logger.debug(
                    f"Skipped duplicate electricity bill: "
                    f"{'property=' + str(property_id) if property_id else 'user=' + str(user_id)} "
                    f"= {bill_amount} rubles"
                )

        except Exception as e:
            logger.error(f"Failed to create readings/bill for {property_name} ({user_name}): {e}")

    return readings_created, bills_created


__all__ = [
    "parse_electricity_row",
    "create_electricity_readings_and_bills",
    "parse_date",
]
