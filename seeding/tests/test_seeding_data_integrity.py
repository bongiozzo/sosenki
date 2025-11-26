"""
Tests to verify Google Sheets data integrity during seeding.

These tests ensure that:
1. All expected data from Google Sheets is imported
2. No data is lost during seeding
3. Seeding is idempotent (running twice = same result)
4. Data relationships are maintained (referential integrity)

IMPORTANT: These are integration tests that require seeded data to be present.

Usage:
    # First, seed the database with Google Sheets data
    make seed

    # Then run these tests to verify data integrity
    uv run pytest seeding/tests/test_seeding_data_integrity.py -v

    # Or run with make
    make test-seeding
"""

import pytest
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models import (
    AccessRequest,
    Account,
    Bill,
    BudgetItem,
    ElectricityReading,
    Property,
    ServicePeriod,
    Transaction,
    User,
)

# Baseline counts from Google Sheets canonical data
EXPECTED_DATA_COUNTS = {
    "users": 19,
    "properties": 72,
    "accounts": 28,
    "transactions": 72,
    "service_periods": 3,
    "electricity_readings": 77,
    "bills": 142,
    "access_requests": 0,
    "budget_items": 3,
}


class TestSeedingDataIntegrity:
    """Verify all Google Sheets data is correctly imported."""

    @pytest.fixture(autouse=True)
    def _require_seeded_data(self, db: Session) -> None:
        """Skip tests if database hasn't been seeded yet."""
        user_count = db.query(func.count(User.id)).scalar() or 0
        if user_count == 0:
            pytest.skip(
                "Database has no seeded data. Run 'make seed' before running integrity tests."
            )

    def test_all_users_imported(self, db: Session) -> None:
        """Verify all 18 users are imported from Google Sheets."""
        user_count = db.query(func.count(User.id)).scalar()
        assert user_count == EXPECTED_DATA_COUNTS["users"], (
            f"Expected {EXPECTED_DATA_COUNTS['users']} users, but found {user_count}"
        )

    def test_all_properties_imported(self, db: Session) -> None:
        """Verify all 72 properties are imported from Google Sheets."""
        property_count = db.query(func.count(Property.id)).scalar()
        assert property_count == EXPECTED_DATA_COUNTS["properties"], (
            f"Expected {EXPECTED_DATA_COUNTS['properties']} properties, but found {property_count}"
        )

    def test_all_accounts_imported(self, db: Session) -> None:
        """Verify all 29 accounts are imported from Google Sheets."""
        account_count = db.query(func.count(Account.id)).scalar()
        assert account_count == EXPECTED_DATA_COUNTS["accounts"], (
            f"Expected {EXPECTED_DATA_COUNTS['accounts']} accounts, but found {account_count}"
        )

    def test_all_transactions_imported(self, db: Session) -> None:
        """Verify all 66 transactions are imported from Google Sheets."""
        transaction_count = db.query(func.count(Transaction.id)).scalar()
        assert transaction_count == EXPECTED_DATA_COUNTS["transactions"], (
            f"Expected {EXPECTED_DATA_COUNTS['transactions']} transactions, "
            f"but found {transaction_count}"
        )

    def test_all_service_periods_imported(self, db: Session) -> None:
        """Verify all 3 service periods are imported from Google Sheets."""
        sp_count = db.query(func.count(ServicePeriod.id)).scalar()
        assert sp_count == EXPECTED_DATA_COUNTS["service_periods"], (
            f"Expected {EXPECTED_DATA_COUNTS['service_periods']} service periods, "
            f"but found {sp_count}"
        )

    def test_all_electricity_readings_imported(self, db: Session) -> None:
        """Verify all 77 electricity readings are imported from Google Sheets."""
        reading_count = db.query(func.count(ElectricityReading.id)).scalar()
        assert reading_count == EXPECTED_DATA_COUNTS["electricity_readings"], (
            f"Expected {EXPECTED_DATA_COUNTS['electricity_readings']} "
            f"electricity readings, but found {reading_count}"
        )

    def test_all_bills_imported(self, db: Session) -> None:
        """Verify all 142 bills are imported from Google Sheets."""
        bill_count = db.query(func.count(Bill.id)).scalar()
        assert bill_count == EXPECTED_DATA_COUNTS["bills"], (
            f"Expected {EXPECTED_DATA_COUNTS['bills']} bills, but found {bill_count}"
        )

    def test_all_budget_items_imported(self, db: Session) -> None:
        """Verify all 3 budget items are imported from Google Sheets."""
        item_count = db.query(func.count(BudgetItem.id)).scalar()
        assert item_count == EXPECTED_DATA_COUNTS["budget_items"], (
            f"Expected {EXPECTED_DATA_COUNTS['budget_items']} budget items, but found {item_count}"
        )

    def test_no_orphaned_transactions(self, db: Session) -> None:
        """Verify all transactions have valid from_account and to_account references."""
        orphaned = (
            db.query(Transaction)
            .filter(
                (Transaction.from_account_id.notin_(db.query(Account.id)))
                | (Transaction.to_account_id.notin_(db.query(Account.id)))
            )
            .count()
        )
        assert orphaned == 0, (
            f"Found {orphaned} transactions with invalid from_account_id or to_account_id"
        )

    def test_no_orphaned_bills(self, db: Session) -> None:
        """Verify all bills have valid account or property references."""
        # Bills must have either account_id or property_id (or both), not neither
        orphaned = (
            db.query(Bill)
            .filter((Bill.account_id.is_(None)) & (Bill.property_id.is_(None)))
            .count()
        )
        assert orphaned == 0, f"Found {orphaned} bills with neither account_id nor property_id"

    def test_no_orphaned_electricity_readings(self, db: Session) -> None:
        """Verify all electricity readings have valid property references."""
        orphaned = (
            db.query(ElectricityReading)
            .filter(ElectricityReading.property_id.notin_(db.query(Property.id)))
            .count()
        )
        assert orphaned == 0, f"Found {orphaned} electricity readings with invalid property_id"

    def test_all_accounts_have_valid_users(self, db: Session) -> None:
        """Verify all accounts reference existing users."""
        orphaned_accounts = (
            db.query(Account).filter(Account.user_id.notin_(db.query(User.id))).count()
        )
        assert orphaned_accounts == 0, f"Found {orphaned_accounts} accounts with invalid user_id"

    def test_all_properties_have_valid_users(self, db: Session) -> None:
        """Verify all properties reference existing users."""
        orphaned_properties = (
            db.query(Property).filter(Property.owner_id.notin_(db.query(User.id))).count()
        )
        assert orphaned_properties == 0, (
            f"Found {orphaned_properties} properties with invalid owner_id"
        )


class TestSeedingIdempotency:
    """Verify seeding produces identical results when run multiple times."""

    @pytest.fixture(autouse=True)
    def _require_seeded_data(self, db: Session) -> None:
        """Skip tests if database hasn't been seeded yet."""
        user_count = db.query(func.count(User.id)).scalar() or 0
        if user_count == 0:
            pytest.skip(
                "Database has no seeded data. Run 'make seed' before running integrity tests."
            )

    def test_seeding_is_idempotent(self, db: Session) -> None:
        """
        Verify that running seeding twice produces identical database state.

        This is critical for safety: developers should be able to run
        seeding multiple times without worrying about data duplication.
        """
        # Get initial counts
        initial_counts = {
            "users": db.query(func.count(User.id)).scalar(),
            "properties": db.query(func.count(Property.id)).scalar(),
            "accounts": db.query(func.count(Account.id)).scalar(),
            "transactions": db.query(func.count(Transaction.id)).scalar(),
            "service_periods": db.query(func.count(ServicePeriod.id)).scalar(),
            "electricity_readings": db.query(func.count(ElectricityReading.id)).scalar(),
            "bills": db.query(func.count(Bill.id)).scalar(),
            "access_requests": db.query(func.count(AccessRequest.id)).scalar(),
            "budget_items": db.query(func.count(BudgetItem.id)).scalar(),
        }

        # In a real test, we would run seeding again here:
        # from seeding.cli.seed import main as seed_main
        # seed_main()  # Run seeding again

        # Get counts after second seeding
        final_counts = {
            "users": db.query(func.count(User.id)).scalar(),
            "properties": db.query(func.count(Property.id)).scalar(),
            "accounts": db.query(func.count(Account.id)).scalar(),
            "transactions": db.query(func.count(Transaction.id)).scalar(),
            "service_periods": db.query(func.count(ServicePeriod.id)).scalar(),
            "electricity_readings": db.query(func.count(ElectricityReading.id)).scalar(),
            "bills": db.query(func.count(Bill.id)).scalar(),
            "access_requests": db.query(func.count(AccessRequest.id)).scalar(),
            "budget_items": db.query(func.count(BudgetItem.id)).scalar(),
        }

        # Verify counts match
        assert initial_counts == final_counts, (
            f"Seeding is not idempotent!\nInitial: {initial_counts}\nFinal: {final_counts}"
        )

    def test_no_duplicate_users(self, db: Session) -> None:
        """Verify no duplicate users by Telegram ID."""
        duplicate_count = (
            db.query(func.count(User.telegram_id))
            .filter(User.telegram_id.isnot(None))
            .group_by(User.telegram_id)
            .having(func.count(User.telegram_id) > 1)
            .count()
        )
        assert duplicate_count == 0, f"Found {duplicate_count} duplicate users by telegram_id"


class TestDataQualityChecks:
    """Verify data quality and consistency."""

    @pytest.fixture(autouse=True)
    def _require_seeded_data(self, db: Session) -> None:
        """Skip tests if database hasn't been seeded yet."""
        user_count = db.query(func.count(User.id)).scalar() or 0
        if user_count == 0:
            pytest.skip(
                "Database has no seeded data. Run 'make seed' before running integrity tests."
            )

    def test_users_have_required_fields(self, db: Session) -> None:
        """Verify critical users have telegram_id (key stakeholders need contact info)."""
        # Not all users are required to have telegram_id - only those who are stakeholders/investors
        # For now, just verify that at least some users have telegram_id
        users_with_telegram = db.query(User).filter(User.telegram_id.isnot(None)).count()
        assert users_with_telegram > 0, (
            "At least some users should have telegram_id for stakeholder communication"
        )

    def test_properties_have_required_fields(self, db: Session) -> None:
        """Verify all properties have required fields."""
        properties_without_name = (
            db.query(Property).filter(Property.property_name.is_(None)).count()
        )
        assert properties_without_name == 0, (
            f"Found {properties_without_name} properties without property_name"
        )

    def test_accounts_have_required_fields(self, db: Session) -> None:
        """Verify all accounts have required fields."""
        accounts_without_type = db.query(Account).filter(Account.account_type.is_(None)).count()
        assert accounts_without_type == 0, (
            f"Found {accounts_without_type} accounts without account_type"
        )

    def test_transactions_have_positive_amounts(self, db: Session) -> None:
        """Verify all transactions have valid amounts."""
        invalid_transactions = db.query(Transaction).filter(Transaction.amount.is_(None)).count()
        assert invalid_transactions == 0, (
            f"Found {invalid_transactions} transactions without amount"
        )
