"""Unit tests for balance service."""

import pytest
from decimal import Decimal

from src.services.balance_service import BalanceService


class TestBalanceService:
    """Test balance service methods."""

    @pytest.fixture
    def service(self):
        """Create balance service instance."""
        return BalanceService()

    def test_calculate_balances_simple(self, service):
        """Test simple balance calculation."""
        contributions = {1: Decimal("100.00"), 2: Decimal("150.00")}
        charges = {1: Decimal("50.00"), 2: Decimal("50.00")}

        result = service.calculate_balances(1, contributions, charges)

        # Owner 1: 100 - 50 = 50 (credit)
        # Owner 2: 150 - 50 = 100 (credit)
        assert result[1] == Decimal("50.00")
        assert result[2] == Decimal("100.00")

    def test_calculate_balances_with_debt(self, service):
        """Test balance calculation with negative balance (debt)."""
        contributions = {1: Decimal("50.00"), 2: Decimal("200.00")}
        charges = {1: Decimal("100.00"), 2: Decimal("50.00")}

        result = service.calculate_balances(1, contributions, charges)

        # Owner 1: 50 - 100 = -50 (owes money)
        # Owner 2: 200 - 50 = 150 (credit)
        assert result[1] == Decimal("-50.00")
        assert result[2] == Decimal("150.00")

    def test_calculate_balances_missing_owners(self, service):
        """Test balance calculation with owners in only one category."""
        contributions = {1: Decimal("100.00"), 2: Decimal("100.00")}
        charges = {1: Decimal("50.00")}  # Owner 2 has no charges

        result = service.calculate_balances(1, contributions, charges)

        # Owner 1: 100 - 50 = 50
        # Owner 2: 100 - 0 = 100 (no charges)
        assert result[1] == Decimal("50.00")
        assert result[2] == Decimal("100.00")

    def test_calculate_balances_empty_contributions(self, service):
        """Test balance with no contributions (all charges)."""
        contributions = {}
        charges = {1: Decimal("50.00"), 2: Decimal("75.00")}

        result = service.calculate_balances(1, contributions, charges)

        # Both owners owe money
        assert result[1] == Decimal("-50.00")
        assert result[2] == Decimal("-75.00")

    def test_calculate_balances_empty_charges(self, service):
        """Test balance with no charges (all credits)."""
        contributions = {1: Decimal("100.00"), 2: Decimal("150.00")}
        charges = {}

        result = service.calculate_balances(1, contributions, charges)

        # All owners have credit
        assert result[1] == Decimal("100.00")
        assert result[2] == Decimal("150.00")

    def test_calculate_balances_zero_amounts(self, service):
        """Test balance calculation with zero amounts."""
        contributions = {1: Decimal("0.00"), 2: Decimal("100.00")}
        charges = {1: Decimal("0.00"), 2: Decimal("100.00")}

        result = service.calculate_balances(1, contributions, charges)

        assert result[1] == Decimal("0.00")
        assert result[2] == Decimal("0.00")

    def test_calculate_balances_precision(self, service):
        """Test balance calculation maintains decimal precision."""
        contributions = {1: Decimal("123.45")}
        charges = {1: Decimal("67.89")}

        result = service.calculate_balances(1, contributions, charges)

        # 123.45 - 67.89 = 55.56
        assert result[1] == Decimal("55.56")

    def test_calculate_balances_many_owners(self, service):
        """Test balance calculation with many owners."""
        contributions = {i: Decimal("100.00") for i in range(1, 51)}  # 50 owners
        charges = {i: Decimal("25.00") for i in range(1, 51)}

        result = service.calculate_balances(1, contributions, charges)

        assert len(result) == 50
        assert all(balance == Decimal("75.00") for balance in result.values())

    def test_calculate_balances_large_amounts(self, service):
        """Test with large monetary amounts."""
        contributions = {1: Decimal("999999.99")}
        charges = {1: Decimal("500000.50")}

        result = service.calculate_balances(1, contributions, charges)

        # 999999.99 - 500000.50 = 499999.49
        assert result[1] == Decimal("499999.49")
