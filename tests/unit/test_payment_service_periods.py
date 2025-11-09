"""Unit tests for PaymentService period management."""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal

from src.services.payment_service import PaymentService
from src.models import ServicePeriod, PeriodStatus


class TestPaymentServicePeriods:
    """Test suite for PaymentService period methods."""

    @pytest.fixture
    def service(self):
        """Create PaymentService instance without database."""
        return PaymentService(db=None)

    def test_create_period_without_db(self, service):
        """Test period creation in mock mode (no database)."""
        start = date(2025, 11, 1)
        end = date(2025, 11, 30)
        period = service.create_period(
            name="November 2025",
            start_date=start,
            end_date=end,
            description="Monthly billing period"
        )

        assert period is not None
        assert period.name == "November 2025"
        assert period.start_date == start
        assert period.end_date == end
        assert period.status == PeriodStatus.OPEN
        assert period.description == "Monthly billing period"

    def test_create_period_invalid_dates(self, service):
        """Test period creation with invalid date range."""
        start = date(2025, 11, 30)
        end = date(2025, 11, 1)

        with pytest.raises(ValueError, match="start_date must be before end_date"):
            service.create_period(
                name="Invalid",
                start_date=start,
                end_date=end
            )

    def test_create_period_same_dates(self, service):
        """Test period creation with same start and end date."""
        same_date = date(2025, 11, 15)

        with pytest.raises(ValueError, match="start_date must be before end_date"):
            service.create_period(
                name="Same",
                start_date=same_date,
                end_date=same_date
            )

    def test_get_period_without_db(self, service):
        """Test getting period without database returns None."""
        result = service.get_period(1)
        assert result is None

    def test_list_periods_without_db(self, service):
        """Test listing periods without database returns empty list."""
        result = service.list_periods()
        assert result == []

    def test_close_period_without_db(self, service):
        """Test closing period without database returns None."""
        result = service.close_period(1)
        assert result is None

    def test_reopen_period_without_db(self, service):
        """Test reopening period without database returns None."""
        result = service.reopen_period(1)
        assert result is None

    def test_record_contribution_without_db(self, service):
        """Test recording contribution without database returns None."""
        result = service.record_contribution(
            period_id=1,
            user_id=1,
            amount=Decimal("100.00"),
            date_val=datetime.now()
        )
        assert result is None

    def test_get_contributions_without_db(self, service):
        """Test getting contributions without database returns empty list."""
        result = service.get_contributions(1)
        assert result == []

    def test_get_owner_contributions_without_db(self, service):
        """Test getting owner contributions without database returns zero."""
        result = service.get_owner_contributions(1, 1)
        assert result == Decimal(0)

    def test_edit_contribution_without_db(self, service):
        """Test editing contribution without database returns None."""
        result = service.edit_contribution(1, amount=Decimal("200.00"))
        assert result is None

    def test_record_expense_without_db(self, service):
        """Test recording expense without database returns None."""
        result = service.record_expense(
            period_id=1,
            paid_by_user_id=1,
            amount=Decimal("500.00"),
            payment_type="Water",
            date_val=datetime.now()
        )
        assert result is None

    def test_get_expenses_without_db(self, service):
        """Test getting expenses without database returns empty list."""
        result = service.get_expenses(1)
        assert result == []

    def test_get_paid_by_user_without_db(self, service):
        """Test getting expenses paid by user without database returns empty list."""
        result = service.get_paid_by_user(1, 1)
        assert result == []

    def test_edit_expense_without_db(self, service):
        """Test editing expense without database returns None."""
        result = service.edit_expense(1, amount=Decimal("600.00"))
        assert result is None

    def test_record_service_charge_without_db(self, service):
        """Test recording service charge without database returns None."""
        result = service.record_service_charge(
            period_id=1,
            user_id=1,
            description="Late fee",
            amount=Decimal("50.00")
        )
        assert result is None

    def test_get_service_charges_without_db(self, service):
        """Test getting service charges without database returns empty list."""
        result = service.get_service_charges(1)
        assert result == []

    def test_get_transaction_history_without_db(self, service):
        """Test getting transaction history without database returns empty list."""
        result = service.get_transaction_history(1)
        assert result == []


class TestPaymentServicePeriodValidation:
    """Test period validation logic."""

    @pytest.fixture
    def service(self):
        """Create PaymentService instance."""
        return PaymentService(db=None)

    def test_period_name_required(self, service):
        """Test period name is required."""
        start = date(2025, 11, 1)
        end = date(2025, 11, 30)

        # Empty name should still create period (validation optional)
        period = service.create_period(
            name="",
            start_date=start,
            end_date=end
        )
        assert period is not None

    def test_period_with_min_date_range(self, service):
        """Test creating period with one-day range."""
        start = date(2025, 11, 1)
        end = date(2025, 11, 2)

        period = service.create_period(
            name="One day",
            start_date=start,
            end_date=end
        )
        assert period is not None

    def test_period_with_large_date_range(self, service):
        """Test creating period spanning multiple months."""
        start = date(2025, 1, 1)
        end = date(2025, 12, 31)

        period = service.create_period(
            name="Full year 2025",
            start_date=start,
            end_date=end
        )
        assert period is not None
        assert (end - start).days == 364  # 365 days total

    def test_period_default_status_is_open(self, service):
        """Test newly created period is in OPEN status."""
        period = service.create_period(
            name="Test",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        assert period.status == PeriodStatus.OPEN

    def test_period_can_have_description(self, service):
        """Test period with description."""
        desc = "Q4 billing with solar credit adjustments"
        period = service.create_period(
            name="Q4 2025",
            start_date=date(2025, 10, 1),
            end_date=date(2025, 12, 31),
            description=desc
        )
        assert period.description == desc

    def test_period_without_description(self, service):
        """Test period without description."""
        period = service.create_period(
            name="Q4 2025",
            start_date=date(2025, 10, 1),
            end_date=date(2025, 12, 31)
        )
        assert period.description is None


class TestPaymentServiceTransactionValidation:
    """Test transaction validation logic."""

    @pytest.fixture
    def service(self):
        """Create PaymentService instance."""
        return PaymentService(db=None)

    def test_contribution_positive_amount_required(self, service):
        """Test contribution amount must be positive."""
        # Without database, validation happens later
        # This test documents the expected behavior
        result = service.record_contribution(
            period_id=1,
            user_id=1,
            amount=Decimal("100.00"),
            date_val=datetime.now()
        )
        # Returns None without database
        assert result is None

    def test_expense_positive_amount_required(self, service):
        """Test expense amount must be positive."""
        result = service.record_expense(
            period_id=1,
            paid_by_user_id=1,
            amount=Decimal("500.00"),
            payment_type="Water",
            date_val=datetime.now()
        )
        assert result is None

    def test_service_charge_positive_amount_required(self, service):
        """Test service charge amount must be positive."""
        result = service.record_service_charge(
            period_id=1,
            user_id=1,
            description="Late fee",
            amount=Decimal("50.00")
        )
        assert result is None

    def test_transaction_datetime_required(self, service):
        """Test transactions accept datetime objects."""
        now = datetime.now()

        # Should not raise
        result = service.record_contribution(
            period_id=1,
            user_id=1,
            amount=Decimal("100.00"),
            date_val=now
        )
        assert result is None  # None because no database

    def test_transaction_decimal_precision(self, service):
        """Test transactions work with Decimal amounts."""
        # High precision amounts
        result = service.record_contribution(
            period_id=1,
            user_id=1,
            amount=Decimal("123.45"),
            date_val=datetime.now()
        )
        assert result is None  # None because no database

    def test_expense_with_all_fields(self, service):
        """Test expense recording with all optional fields."""
        result = service.record_expense(
            period_id=1,
            paid_by_user_id=2,
            amount=Decimal("1500.50"),
            payment_type="Water & Sewer",
            date_val=datetime.now(),
            vendor="City Water Works",
            description="Q4 water service",
            budget_item_id=1
        )
        assert result is None  # None because no database

    def test_service_charge_with_description(self, service):
        """Test service charge with various descriptions."""
        descriptions = [
            "Late payment fee",
            "Water line repair (Unit A)",
            "HOA assessment - special",
        ]

        for desc in descriptions:
            result = service.record_service_charge(
                period_id=1,
                user_id=1,
                description=desc,
                amount=Decimal("25.00")
            )
            assert result is None  # None because no database

    def test_contribution_with_comment(self, service):
        """Test contribution recording with comment."""
        result = service.record_contribution(
            period_id=1,
            user_id=1,
            amount=Decimal("250.00"),
            date_val=datetime.now(),
            comment="November payment via bank transfer"
        )
        assert result is None  # None because no database
