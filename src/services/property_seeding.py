"""Property parsing and creation utilities for database seeding.

Handles property parsing, "Доп" column splitting, selective attribute inheritance,
and type mapping for auxiliary properties.
"""

import logging
from typing import Dict, List

from sqlalchemy.orm import Session

from src.models.property import Property
from src.models.user import User
from src.services.errors import DataValidationError
from src.services.parsers import (
    parse_boolean,
    parse_russian_currency,
    parse_russian_decimal,
)

# Type mapping for "Доп" column values
DOP_TYPE_MAPPING = {
    "26": "Малый",
    "4": "Беседка",
    "69": "Хоздвор",
    "70": "Хоздвор",
    "71": "Хоздвор",
    "72": "Хоздвор",
    "73": "Хоздвор",
    "74": "Хоздвор",
    "49": "Склад",
}

DEFAULT_TYPE = "Баня"


def parse_property_row(
    row_dict: Dict[str, str], owner: User
) -> List[Dict]:
    """
    Parse a row from "Дома" sheet into one or more Property records.

    Creates main property from row data, plus additional properties from
    "Доп" column if present.

    Args:
        row_dict: Dictionary mapping column names to cell values
        owner: User instance (property owner)

    Returns:
        List of dicts with Property attributes (main + additional)
        Empty list if row should be skipped

    Raises:
        DataValidationError: On validation errors

    Parsing Rules (main property):
    1. property_name from "Дом" column (required)
    2. type from "Размер" column
    3. share_weight from "Коэффициент" column (Russian decimal)
    4. is_ready from "Готовность" column (Да=True)
    5. is_for_tenant from "Аренда" column (Да=True)
    6. photo_link from "Фото" column (URL)
    7. sale_price from "Цена" column (Russian currency)
    8. owner_id from owner parameter
    9. is_active = True (new properties are active)

    Parsing Rules ("Доп" column - additional properties):
    10. Split "Доп" by commas to get list of property codes
    11. For each code, create additional Property with:
        - property_name = code value (trimmed)
        - type = map code to type (26→Малый, etc.)
        - owner_id = inherited from main row
        - is_ready = inherited from main row
        - is_for_tenant = inherited from main row
        - share_weight = NULL
        - photo_link = NULL
        - sale_price = NULL
        - is_active = True
    """
    logger = logging.getLogger("sostenki.seeding.properties")
    properties = []

    try:
        # Main property parsing
        property_name = row_dict.get("Дом", "").strip()
        if not property_name:
            logger.warning("Skipping row: empty property_name (Дом column)")
            return []

        # Parse numeric fields
        try:
            share_weight = parse_russian_decimal(
                row_dict.get("Коэффициент", "")
            )
        except ValueError as e:
            logger.warning(f"Invalid share_weight format: {e}, skipping row")
            return []

        try:
            sale_price = parse_russian_currency(
                row_dict.get("Цена", "")
            )
        except ValueError as e:
            logger.warning(f"Invalid sale_price format: {e}, skipping row")
            return []

        # Main property attributes
        main_property = {
            "owner_id": owner.id,
            "property_name": property_name,
            "type": row_dict.get("Размер", "").strip(),
            "share_weight": share_weight,
            "is_ready": parse_boolean(row_dict.get("Готовность", "")),
            "is_for_tenant": parse_boolean(row_dict.get("Аренда", "")),
            "photo_link": row_dict.get("Фото", "").strip() or None,
            "sale_price": sale_price,
            "is_active": True,
        }
        properties.append(main_property)
        logger.debug(f"Parsed main property: {property_name}")

        # Process "Доп" column for additional properties
        dop_value = row_dict.get("Доп", "").strip()
        if dop_value:
            # Split by comma and create additional properties
            dop_codes = [code.strip() for code in dop_value.split(",")]

            for code in dop_codes:
                if not code:  # Skip empty codes
                    continue

                # Map code to property type
                property_type = DOP_TYPE_MAPPING.get(code, DEFAULT_TYPE)

                # Additional property attributes (selective inheritance)
                additional_property = {
                    "owner_id": owner.id,  # Inherited
                    "property_name": code,  # The code value itself
                    "type": property_type,  # Derived from mapping
                    "share_weight": None,  # NULL (not allocated)
                    "is_ready": main_property["is_ready"],  # Inherited
                    "is_for_tenant": main_property["is_for_tenant"],  # Inherited
                    "photo_link": None,  # NULL
                    "sale_price": None,  # NULL
                    "is_active": True,
                }
                properties.append(additional_property)
                logger.debug(
                    f"Parsed additional property from Доп: {code} → {property_type}"
                )

        return properties

    except Exception as e:
        raise DataValidationError(f"Failed to parse property row: {e}") from e


def create_properties(
    session: Session, property_dicts: List[Dict], owner: User
) -> List[Property]:
    """
    Create Property records in database.

    Args:
        session: SQLAlchemy session
        property_dicts: List of dicts with property attributes
        owner: Owner user for logging/reference

    Returns:
        List of created Property instances

    Raises:
        DataValidationError: On database errors
    """
    logger = logging.getLogger("sostenki.seeding.properties")
    created = []

    try:
        for prop_dict in property_dicts:
            prop = Property(**prop_dict)
            session.add(prop)
            session.flush()  # Get ID before full commit
            created.append(prop)
            logger.debug(f"Added property to session: {prop.property_name}")

        return created

    except Exception as e:
        raise DataValidationError(f"Failed to create properties: {e}") from e
