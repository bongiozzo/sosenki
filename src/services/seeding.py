"""Seeding orchestration - main coordinator for database seeding process.

Orchestrates the complete pipeline:
1. Fetch data from Google Sheets
2. Parse users and properties
3. Truncate existing data
4. Insert new data atomically
5. Commit or rollback on error
"""

import logging
from dataclasses import dataclass
from typing import Dict, List

from sqlalchemy import delete
from sqlalchemy.orm import Session

from src.models.property import Property
from src.models.user import User
from src.services.errors import DatabaseError, TransactionError
from src.services.google_sheets import GoogleSheetsClient
from src.services.property_seeding import create_properties, parse_property_row
from src.services.seeding_utils import (
    get_or_create_user,
    parse_user_row,
    sheet_row_to_dict,
)


@dataclass
class SeedResult:
    """Result of a seeding operation."""

    success: bool
    """Whether seeding completed successfully"""

    users_created: int
    """Number of users created or updated"""

    properties_created: int
    """Number of properties created"""

    rows_skipped: int
    """Number of rows skipped due to validation errors"""

    error_message: str = None
    """Error message if success=False"""

    def __str__(self) -> str:
        """Format result as human-readable string."""
        if self.success:
            return (
                f"✓ Seed successful\n"
                f"  Users: {self.users_created}\n"
                f"  Properties: {self.properties_created}\n"
                f"  Skipped: {self.rows_skipped}"
            )
        else:
            return f"✗ Seed failed: {self.error_message}"


class SeededService:
    """Orchestrates database seeding process."""

    def __init__(self, session: Session, logger: logging.Logger = None):
        """
        Initialize seeding service.

        Args:
            session: SQLAlchemy database session
            logger: Optional logger instance (creates if not provided)
        """
        self.session = session
        self.logger = logger or logging.getLogger("sostenki.seeding.main")

    def execute_seed(
        self,
        google_sheets_client: GoogleSheetsClient,
        spreadsheet_id: str,
        sheet_name: str,
    ) -> SeedResult:
        """
        Execute the complete seeding process.

        Orchestration steps:
        1. Fetch data from Google Sheets
        2. Parse header row to get column names
        3. Parse each data row into users and properties
        4. Truncate existing users and properties tables
        5. Insert all new records atomically
        6. Commit on success, rollback on error

        Args:
            google_sheets_client: GoogleSheetsClient instance
            spreadsheet_id: Google Sheet ID
            sheet_name: Sheet name (e.g., "Дома")

        Returns:
            SeedResult with counts and status

        Transaction Semantics:
        - All operations (truncate + insert) happen in single transaction
        - Either all-or-nothing: complete success or complete rollback
        - If error occurs during insert, no partial data remains
        """
        try:
            self.logger.info("Starting database seeding...")

            # Step 1: Fetch data from Google Sheets
            self.logger.info(
                f"Fetching data from sheet '{sheet_name}'..."
            )
            sheet_data = google_sheets_client.fetch_sheet_data(
                spreadsheet_id, sheet_name
            )

            if not sheet_data:
                raise DatabaseError(f"Sheet '{sheet_name}' is empty")

            # Step 2: Extract header row
            # The sheet has a blank row at the top, so real headers are in row 1 (index 1)
            header_row = sheet_data[1]
            data_rows = sheet_data[2:]
            self.logger.info(
                f"Found {len(data_rows)} data rows with {len(header_row)} columns"
            )

            # Step 3: Parse all rows into users and properties
            self.logger.info("Parsing users and properties...")
            users_dict: Dict[str, dict] = {}  # name -> user_attrs
            property_rows: List[tuple] = []  # (user_name, property_dicts)
            rows_skipped = 0

            for row_idx, row_values in enumerate(data_rows, start=2):
                try:
                    # Convert row to dictionary using header names
                    row_dict = sheet_row_to_dict(row_values, header_row)

                    # Parse user attributes
                    try:
                        user_attrs = parse_user_row(row_dict)
                        owner_name = user_attrs["name"]
                        users_dict[owner_name] = user_attrs
                    except Exception:
                        # Skip if user parsing fails
                        rows_skipped += 1
                        continue

                    # Store for property parsing (after users are created)
                    property_rows.append((owner_name, row_dict))

                except Exception as e:
                    self.logger.warning(
                        f"Row {row_idx}: Failed to parse row: {e}"
                    )
                    rows_skipped += 1

            self.logger.info(
                f"Parsed {len(users_dict)} unique users, "
                f"{len(property_rows)} property rows, skipped {rows_skipped}"
            )

            # Step 4: Truncate existing data (atomic with inserts)
            try:
                self.logger.info("Truncating existing data...")
                self.session.execute(delete(Property))
                self.session.execute(delete(User))
                self.logger.info("Tables truncated")
            except Exception as e:
                raise TransactionError(f"Failed to truncate tables: {e}") from e

            # Step 5: Insert users
            try:
                self.logger.info(f"Creating {len(users_dict)} users...")
                created_users: Dict[str, User] = {}

                for user_name, user_attrs in users_dict.items():
                    user = get_or_create_user(
                        self.session, user_name, user_attrs
                    )
                    created_users[user_name] = user

                self.logger.info(f"Created {len(created_users)} users")
            except Exception as e:
                raise TransactionError(f"Failed to create users: {e}") from e

            # Step 6: Insert properties
            try:
                self.logger.info("Creating properties...")
                total_properties = 0

                for owner_name, row_dict in property_rows:
                    owner = created_users.get(owner_name)
                    if not owner:
                        self.logger.warning(
                            f"Owner not found: {owner_name}, skipping property"
                        )
                        continue

                    # Parse property row (may create multiple properties from "Доп" column)
                    try:
                        property_dicts = parse_property_row(row_dict, owner)
                        if property_dicts:
                            create_properties(
                                self.session, property_dicts, owner
                            )
                            total_properties += len(property_dicts)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to parse property for owner "
                            f"'{owner_name}': {e}"
                        )
                        rows_skipped += 1

                self.logger.info(f"Created {total_properties} properties")
            except Exception as e:
                raise TransactionError(f"Failed to create properties: {e}") from e

            # Step 7: Commit transaction
            try:
                self.session.commit()
                self.logger.info("✓ Seed committed successfully")
                return SeedResult(
                    success=True,
                    users_created=len(created_users),
                    properties_created=total_properties,
                    rows_skipped=rows_skipped,
                )
            except Exception as e:
                raise TransactionError(f"Failed to commit transaction: {e}") from e

        except Exception as e:
            # Rollback on any error
            try:
                self.session.rollback()
                self.logger.error(
                    f"Seeding failed; changes rolled back: {e}"
                )
            except Exception as rollback_error:
                self.logger.error(
                    f"Rollback failed: {rollback_error}"
                )

            return SeedResult(
                success=False,
                users_created=0,
                properties_created=0,
                rows_skipped=0,
                error_message=str(e),
            )
