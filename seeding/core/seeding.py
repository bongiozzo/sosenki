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

from seeding.config.seeding_config import SeedingConfig
from seeding.core.bills_seeding import create_bills
from seeding.core.credit_seeding import parse_credit_row
from seeding.core.debit_seeding import parse_debit_row
from seeding.core.errors import DatabaseError, TransactionError
from seeding.core.google_sheets import GoogleSheetsClient
from seeding.core.property_seeding import create_properties, parse_property_row
from seeding.core.seeding_utils import (
    get_or_create_user,
    parse_user_row,
    sheet_row_to_dict,
)
from seeding.core.shared_electricity_bill_seeding import create_shared_electricity_bills
from seeding.core.transaction_seeding import (
    create_credit_transactions,
    create_debit_transactions,
    get_or_create_service_period,
)
from src.models.account import Account
from src.models.property import Property
from src.models.user import User


@dataclass
class SeedResult:
    """Result of a seeding operation."""

    success: bool
    """Whether seeding completed successfully"""

    users_created: int
    """Number of users created or updated"""

    properties_created: int
    """Number of properties created"""

    debits_created: int
    """Number of debits created"""

    credits_created: int = 0
    """Number of credits (from credit transactions) created"""

    electricity_readings_created: int = 0
    """Number of electricity readings created"""

    electricity_bills_created: int = 0
    """Number of electricity bills created"""

    shared_electricity_bills_created: int = 0
    """Number of shared electricity bills created"""

    bills_created: int = 0
    """Number of regular bills (conservation, main, etc.) created"""

    rows_skipped: int = 0
    """Number of rows skipped due to validation errors"""

    error_message: str | None = None
    """Error message if success=False"""

    def __str__(self) -> str:
        """Format result as human-readable string."""
        if self.success:
            return (
                f"✓ Seed successful\n"
                f"  Users: {self.users_created}\n"
                f"  Properties: {self.properties_created}\n"
                f"  Debits: {self.debits_created}\n"
                f"  Credits: {self.credits_created}\n"
                f"  Electricity readings: {self.electricity_readings_created}\n"
                f"  Electricity bills: {self.electricity_bills_created}\n"
                f"  Shared electricity bills: {self.shared_electricity_bills_created}\n"
                f"  Bills (conservation/main): {self.bills_created}\n"
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
        self.logger = logger or logging.getLogger("sosenki.seeding.main")

    def _process_transaction_range(
        self,
        google_sheets_client: GoogleSheetsClient,
        spreadsheet_id: str,
        range_names: List[str],
        service_periods_map: Dict[str, Dict],
        user_map: Dict[str, User],
        parse_func,
        create_func,
        transaction_type: str = "transaction",
        extra_args: Dict = None,
    ) -> int:
        """Process a set of transaction ranges from Google Sheets.

        Args:
            google_sheets_client: GoogleSheetsClient instance
            spreadsheet_id: Google Sheet ID
            range_names: List of named ranges to process
            service_periods_map: Unified service periods mapping
            user_map: User name -> User object mapping
            parse_func: Row parsing function
            create_func: Transaction creation function
            transaction_type: Type of transaction (for logging)
            extra_args: Extra arguments to pass to parse_func and create_func

        Returns:
            Total number of transactions created
        """
        extra_args = extra_args or {}
        total_created = 0
        rows_skipped = 0

        for range_name in range_names:
            self.logger.info(f"Fetching {transaction_type}s from range '{range_name}'...")

            try:
                sheet_data = google_sheets_client.fetch_sheet_data(
                    spreadsheet_id, range_spec=range_name
                )

                if not sheet_data or len(sheet_data) < 2:
                    self.logger.warning(f"Range '{range_name}' has insufficient data")
                    continue

                header_row = sheet_data[0]
                data_rows = sheet_data[1:]

                # Parse rows
                row_dicts: List[Dict] = []
                for row_idx, row_values in enumerate(data_rows, start=1):
                    try:
                        row_dict = sheet_row_to_dict(row_values, header_row)
                        # Call appropriate parse function
                        if transaction_type == "debit":
                            parsed = parse_func(
                                row_dict,
                                extra_args.get("account_column"),
                                extra_args.get("config"),
                            )
                        else:
                            parsed = parse_func(row_dict)

                        if parsed:
                            row_dicts.append(parsed)
                    except Exception as e:
                        self.logger.debug(
                            f"{transaction_type.capitalize()} row {row_idx}: Skipped ({e})"
                        )
                        rows_skipped += 1

                self.logger.info(
                    f"Parsed {len(row_dicts)} {transaction_type} records from '{range_name}'"
                )

                # Get service period for this range
                if row_dicts and range_name in service_periods_map:
                    try:
                        period_info = service_periods_map[range_name]

                        service_period = get_or_create_service_period(
                            self.session,
                            period_info.get("name"),  # Period name (e.g., "2024-2025")
                            period_info.get("start_date"),
                            period_info.get("end_date"),
                        )

                        # Create transactions
                        range_created = create_func(
                            self.session,
                            row_dicts,
                            user_map=user_map,
                            period=service_period,
                            default_account_name=extra_args.get("default_account_name", "Взносы"),
                        )
                        total_created += range_created
                    except Exception as e:
                        self.logger.error(
                            f"Failed to create {transaction_type}s from '{range_name}': {e}"
                        )
                        rows_skipped += len(row_dicts)

            except Exception as e:
                self.logger.error(f"Failed to process range '{range_name}': {e}")

        return total_created

    def execute_seed(  # noqa: C901
        self,
        google_sheets_client: GoogleSheetsClient,
        spreadsheet_id: str,
    ) -> SeedResult:
        """
        Execute the complete seeding process.

        Orchestration steps:
        1. Fetch data from Google Sheets (using named ranges from config)
        2. Parse header row to get column names
        3. Parse each data row into users and properties
        4. Truncate existing users and properties tables
        5. Insert all new records atomically
        6. Commit on success, rollback on error

        Args:
            google_sheets_client: GoogleSheetsClient instance
            spreadsheet_id: Google Sheet ID

        Returns:
            SeedResult with counts and status

        Transaction Semantics:
        - All operations (truncate + insert) happen in single transaction
        - Either all-or-nothing: complete success or complete rollback
        - If error occurs during insert, no partial data remains
        """
        try:
            self.logger.info("Starting database seeding...")

            # Load configuration
            config = SeedingConfig.load()

            # Step 1: Fetch data from Google Sheets using named range
            user_range_name = config.get_user_range_name()
            self.logger.info(f"Fetching data from named range '{user_range_name}'...")
            sheet_data = google_sheets_client.fetch_sheet_data(
                spreadsheet_id, range_spec=user_range_name
            )

            if not sheet_data:
                raise DatabaseError(f"Range '{user_range_name}' is empty")

            # Step 2: Extract header row
            # Named ranges: header at [0], data from [1:]
            header_row = sheet_data[0]
            data_rows = sheet_data[1:]
            self.logger.info(f"Found {len(data_rows)} data rows with {len(header_row)} columns")

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
                    self.logger.warning(f"Row {row_idx}: Failed to parse row: {e}")
                    rows_skipped += 1

            self.logger.info(
                f"Parsed {len(users_dict)} unique users, "
                f"{len(property_rows)} property rows, skipped {rows_skipped}"
            )

            # Step 3b: Add users from 'add' section of config
            additional_users = config.get_additional_users()
            if additional_users:
                self.logger.info(f"Found {len(additional_users)} additional users to add")
                for user_name, user_attrs in additional_users.items():
                    if user_name not in users_dict:
                        # Merge with defaults to ensure all required fields are present
                        merged_attrs = config.get_user_defaults().copy()
                        merged_attrs.update(user_attrs)
                        merged_attrs["name"] = user_name
                        users_dict[user_name] = merged_attrs
                        self.logger.info(f"Added user from config: {user_name}")
                    else:
                        self.logger.info(f"User already exists (from sheet): {user_name}, skipping")

            # Step 4: Truncate existing data (atomic with inserts)
            try:
                self.logger.info("Truncating existing data...")
                # Delete in correct order to respect foreign keys
                self.session.execute(delete(Account))
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
                    user = get_or_create_user(self.session, user_name, user_attrs)
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
                        self.logger.warning(f"Owner not found: {owner_name}, skipping property")
                        continue

                    # Parse property row (may create multiple properties from "Доп" column)
                    try:
                        property_dicts = parse_property_row(row_dict, owner)
                        if property_dicts:
                            create_properties(self.session, property_dicts, owner)
                            total_properties += len(property_dicts)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to parse property for owner '{owner_name}': {e}"
                        )
                        rows_skipped += 1

                self.logger.info(f"Created {total_properties} properties")
            except Exception as e:
                raise TransactionError(f"Failed to create properties: {e}") from e

            # Step 7: Pre-create all service periods from config
            # This ensures all periods exist even if no data is processed for them
            try:
                service_periods_map = config.get_service_periods()

                for _, period_info in service_periods_map.items():
                    get_or_create_service_period(
                        self.session,
                        period_info.get("name"),
                        period_info.get("start_date"),
                        period_info.get("end_date"),
                    )

                self.logger.info(f"✓ Pre-created {len(service_periods_map)} service periods")
            except Exception as e:
                raise TransactionError(f"Failed to create service periods: {e}") from e

            # Step 8: Process transactions (debits and credits) from seeding config
            # Uses unified service periods from config
            total_debits = 0
            total_credits = 0
            total_electricity_readings = 0
            total_electricity_bills = 0
            try:
                # Get unified service periods and transaction range mappings
                service_periods_map = config.get_service_periods()
                debit_ranges = config.get_debit_range_names()
                credit_ranges = config.get_credit_range_names()

                # Process debit transactions
                if debit_ranges:
                    default_account_name = config.get_debit_account_name()
                    account_column = config.get_debit_account_column()
                    self.logger.info(f"Processing {len(debit_ranges)} debit range(s)")

                    total_debits = self._process_transaction_range(
                        google_sheets_client,
                        spreadsheet_id,
                        debit_ranges,
                        service_periods_map,
                        created_users,
                        parse_debit_row,
                        create_debit_transactions,
                        transaction_type="debit",
                        extra_args={
                            "account_column": account_column,
                            "config": config,
                            "default_account_name": default_account_name,
                        },
                    )

                # Process credit transactions
                if credit_ranges:
                    self.logger.info(f"Processing {len(credit_ranges)} credit range(s)")

                    total_credits = self._process_transaction_range(
                        google_sheets_client,
                        spreadsheet_id,
                        credit_ranges,
                        service_periods_map,
                        created_users,
                        parse_credit_row,
                        create_credit_transactions,
                        transaction_type="credit",
                        extra_args={"default_account_name": "Взносы"},
                    )

            except Exception as e:
                self.logger.error(f"Failed to process transactions: {e}")
                # Don't fail entire seeding if transactions fail - just log and continue

            # Step 9: Process electricity readings
            total_electricity_readings = 0
            total_electricity_bills = 0
            try:
                from seeding.core.electricity_seeding import (
                    create_electricity_readings_and_bills,
                    parse_electricity_row,
                )
                from seeding.core.parsers import parse_date

                elec_range_names = config.get_electricity_range_names()

                if elec_range_names:
                    elec_service_periods_map = config.get_schema_service_periods(
                        "electricity_readings"
                    )
                    self.logger.info(
                        f"Processing {len(elec_range_names)} electricity reading range(s)"
                    )

                    for elec_range_name in elec_range_names:
                        self.logger.info(
                            f"Fetching electricity readings from range '{elec_range_name}'..."
                        )

                        try:
                            sheet_data = google_sheets_client.fetch_sheet_data(
                                spreadsheet_id, range_spec=elec_range_name
                            )

                            if not sheet_data or len(sheet_data) < 2:
                                self.logger.warning(
                                    f"Range '{elec_range_name}' has insufficient data"
                                )
                                continue

                            header_row = sheet_data[0]
                            data_rows = sheet_data[1:]

                            # Parse rows
                            reading_dicts: List[Dict] = []
                            for row_idx, row_values in enumerate(data_rows, start=1):
                                try:
                                    row_dict = sheet_row_to_dict(row_values, header_row)
                                    parsed = parse_electricity_row(row_dict, config)
                                    if parsed:
                                        reading_dicts.append(parsed)
                                except Exception as e:
                                    self.logger.debug(f"Electricity row {row_idx}: Skipped ({e})")
                                    rows_skipped += 1

                            self.logger.info(
                                f"Parsed {len(reading_dicts)} electricity readings from '{elec_range_name}'"
                            )

                            # Get service period for this range
                            if reading_dicts and elec_range_name in elec_service_periods_map:
                                try:
                                    period_info = elec_service_periods_map[elec_range_name]
                                    period_start_date = parse_date(period_info.get("start_date"))
                                    period_end_date = parse_date(period_info.get("end_date"))

                                    # Get service period object
                                    service_period = get_or_create_service_period(
                                        self.session,
                                        period_info.get("name"),
                                        period_info.get("start_date"),
                                        period_info.get("end_date"),
                                    )

                                    # Create readings and bills
                                    range_readings, range_bills = (
                                        create_electricity_readings_and_bills(
                                            self.session,
                                            reading_dicts,
                                            user_map=created_users,
                                            service_period_id=service_period.id,
                                            period_start_date=period_start_date,
                                            period_end_date=period_end_date,
                                        )
                                    )

                                    total_electricity_readings += range_readings
                                    total_electricity_bills += range_bills

                                except Exception as e:
                                    self.logger.error(
                                        f"Failed to create readings/bills from '{elec_range_name}': {e}"
                                    )

                        except Exception as e:
                            self.logger.error(f"Failed to process range '{elec_range_name}': {e}")
                else:
                    self.logger.info("No electricity reading ranges configured")

            except Exception as e:
                self.logger.error(f"Failed to process electricity readings: {e}")

            # Step 10: Process shared electricity bills
            total_shared_electricity_bills = 0
            try:
                config = SeedingConfig.load()
                shared_bill_range_names = config.get_shared_electricity_bill_range_names()

                if shared_bill_range_names:
                    shared_parsing_rules = config.get_shared_electricity_parsing_rules()
                    shared_name_based_rules = config.get_shared_electricity_name_based_rules()
                    shared_service_periods_map = config.get_schema_service_periods(
                        "shared_electricity_bills"
                    )
                    self.logger.info(
                        f"Processing {len(shared_bill_range_names)} shared electricity bill ranges..."
                    )

                    for shared_range_name in shared_bill_range_names:
                        self.logger.info(
                            f"Fetching shared electricity bills from range '{shared_range_name}'..."
                        )

                        try:
                            sheet_data = google_sheets_client.fetch_sheet_data(
                                spreadsheet_id, range_spec=shared_range_name
                            )

                            if not sheet_data or len(sheet_data) < 2:
                                self.logger.warning(
                                    f"Range '{shared_range_name}' has insufficient data"
                                )
                                continue

                            header_row = sheet_data[0]
                            data_rows = sheet_data[1:]

                            # Parse rows into bill dictionaries
                            bill_dicts: List[Dict] = []
                            for row_idx, row_values in enumerate(data_rows, start=1):
                                try:
                                    row_dict = sheet_row_to_dict(row_values, header_row)
                                    # Map column names to field names
                                    parsed = {
                                        "user": row_dict.get(shared_parsing_rules.get("user")),
                                        "amount": row_dict.get(shared_parsing_rules.get("amount")),
                                    }
                                    if parsed.get("user") or parsed.get("amount"):
                                        bill_dicts.append(parsed)
                                except Exception as e:
                                    self.logger.debug(f"Shared bill row {row_idx}: Skipped ({e})")
                                    rows_skipped += 1

                            self.logger.info(
                                f"Parsed {len(bill_dicts)} shared electricity bills from '{shared_range_name}'"
                            )

                            # Get service period for this range
                            if bill_dicts and shared_range_name in shared_service_periods_map:
                                try:
                                    period_info = shared_service_periods_map[shared_range_name]

                                    # Get service period object
                                    service_period = get_or_create_service_period(
                                        self.session,
                                        period_info.get("name"),
                                        period_info.get("start_date"),
                                        period_info.get("end_date"),
                                    )

                                    # Create shared bills with name-based split rules
                                    range_shared_bills = create_shared_electricity_bills(
                                        bill_dicts,
                                        user_map=created_users,
                                        service_period=service_period,
                                        session=self.session,
                                        name_based_rules=shared_name_based_rules,
                                    )

                                    total_shared_electricity_bills += range_shared_bills
                                    self.logger.info(
                                        f"✓ Created {range_shared_bills} shared electricity bills from '{shared_range_name}'"
                                    )

                                except Exception as e:
                                    self.logger.error(
                                        f"Failed to create shared bills from '{shared_range_name}': {e}",
                                        exc_info=True,
                                    )

                        except Exception as e:
                            self.logger.error(f"Failed to process range '{shared_range_name}': {e}")
                else:
                    self.logger.info("No shared electricity bill ranges configured")

            except Exception as e:
                self.logger.error(f"Failed to process shared electricity bills: {e}")

            # Step 11: Process bills (conservation, main, etc.)
            total_bills = 0
            try:
                config = SeedingConfig.load()
                bills_range_names = config.get_bills_range_names()

                if bills_range_names:
                    bills_parsing_rules = config.get_bills_parsing_rules()
                    bills_name_based_rules = config.get_bills_name_based_rules()
                    bills_service_periods_map = config.get_schema_service_periods("bills")
                    self.logger.info(f"Processing {len(bills_range_names)} bills range(s)...")

                    for bills_range_name in bills_range_names:
                        self.logger.info(f"Fetching bills from range '{bills_range_name}'...")

                        try:
                            sheet_data = google_sheets_client.fetch_sheet_data(
                                spreadsheet_id, range_spec=bills_range_name
                            )

                            if not sheet_data or len(sheet_data) < 2:
                                self.logger.warning(
                                    f"Range '{bills_range_name}' has insufficient data"
                                )
                                continue

                            header_row = sheet_data[0]
                            data_rows = sheet_data[1:]

                            # Parse rows into bill dictionaries
                            bill_dicts: List[Dict] = []
                            for row_idx, row_values in enumerate(data_rows, start=1):
                                try:
                                    row_dict = sheet_row_to_dict(row_values, header_row)
                                    # Map column names to field names
                                    parsed = {
                                        "user": row_dict.get(bills_parsing_rules.get("user")),
                                        "amount": row_dict.get(bills_parsing_rules.get("amount")),
                                        "conservation": row_dict.get(
                                            bills_parsing_rules.get("conservation", "")
                                        ),
                                    }
                                    if parsed.get("user") or parsed.get("amount"):
                                        bill_dicts.append(parsed)
                                except Exception as e:
                                    self.logger.debug(f"Bills row {row_idx}: Skipped ({e})")
                                    rows_skipped += 1

                            self.logger.info(
                                f"Parsed {len(bill_dicts)} bills from '{bills_range_name}'"
                            )

                            # Get service period for this range
                            if bill_dicts and bills_range_name in bills_service_periods_map:
                                try:
                                    period_info = bills_service_periods_map[bills_range_name]

                                    # Get service period object
                                    service_period = get_or_create_service_period(
                                        self.session,
                                        period_info.get("name"),
                                        period_info.get("start_date"),
                                        period_info.get("end_date"),
                                    )

                                    # Create bills with name-based split rules
                                    range_bills = create_bills(
                                        bill_dicts,
                                        user_map=created_users,
                                        service_period=service_period,
                                        session=self.session,
                                        name_based_rules=bills_name_based_rules,
                                    )

                                    total_bills += range_bills
                                    self.logger.info(
                                        f"✓ Created {range_bills} bills from '{bills_range_name}'"
                                    )

                                except Exception as e:
                                    self.logger.error(
                                        f"Failed to create bills from '{bills_range_name}': {e}",
                                        exc_info=True,
                                    )

                        except Exception as e:
                            self.logger.error(f"Failed to process range '{bills_range_name}': {e}")
                else:
                    self.logger.info("No bills ranges configured")

            except Exception as e:
                self.logger.error(f"Failed to process bills: {e}")

            # Step 12: Commit transaction
            try:
                self.session.commit()
                self.logger.info("✓ Seed committed successfully")
                return SeedResult(
                    success=True,
                    users_created=len(created_users),
                    properties_created=total_properties,
                    debits_created=total_debits,
                    credits_created=total_credits,
                    electricity_readings_created=total_electricity_readings,
                    electricity_bills_created=total_electricity_bills,
                    shared_electricity_bills_created=total_shared_electricity_bills,
                    bills_created=total_bills,
                    rows_skipped=rows_skipped,
                )
            except Exception as e:
                raise TransactionError(f"Failed to commit transaction: {e}") from e

        except Exception as e:
            # Rollback on any error
            try:
                self.session.rollback()
                self.logger.error(f"Seeding failed; changes rolled back: {e}")
            except Exception as rollback_error:
                self.logger.error(f"Rollback failed: {rollback_error}")

            return SeedResult(
                success=False,
                users_created=0,
                properties_created=0,
                debits_created=0,
                credits_created=0,
                electricity_readings_created=0,
                electricity_bills_created=0,
                rows_skipped=0,
                error_message=str(e),
            )
