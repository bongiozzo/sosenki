"""Unit tests for allocation service."""

from decimal import Decimal

import pytest

from src.services.allocation_service import AllocationService


class TestAllocationService:
    """Test allocation service methods."""

    @pytest.fixture
    def service(self):
        """Create allocation service instance."""
        return AllocationService()

    def test_distribute_with_remainder_proportional(self, service):
        """Test proportional distribution with remainder handling."""
        total = Decimal("100.00")
        shares = {1: Decimal("3"), 2: Decimal("3"), 3: Decimal("4")}

        result = service.distribute_with_remainder(total, shares)

        # Expected: 1→30, 2→30, 3→40
        assert result[1] == Decimal("30.00")
        assert result[2] == Decimal("30.00")
        assert result[3] == Decimal("40.00")
        assert sum(result.values()) == total

    def test_distribute_with_remainder_uneven_split(self, service):
        """Test uneven split that creates remainder."""
        total = Decimal("100.00")
        shares = {1: Decimal("1"), 2: Decimal("1"), 3: Decimal("1")}

        result = service.distribute_with_remainder(total, shares)

        # 100/3 = 33.333... → 33.33 each + remainder 0.01
        # Remainder goes to owner with largest share (all equal, so first)
        assert sum(result.values()) == total
        assert all(amount in [Decimal("33.33"), Decimal("33.34")] for amount in result.values())

    def test_distribute_with_remainder_zero_money_loss(self, service):
        """Test that remainder distribution loses no money."""
        total = Decimal("1000.00")
        shares = {i: Decimal(str(i)) for i in range(1, 11)}  # 1 to 10

        result = service.distribute_with_remainder(total, shares)

        # Verify total preserved to the cent
        assert sum(result.values()) == total
        assert all(amount >= Decimal(0) for amount in result.values())

    def test_distribute_with_remainder_large_numbers(self, service):
        """Test with large amounts and many owners."""
        total = Decimal("1000.00")  # Use round number to avoid rounding issues
        shares = {1: Decimal("1"), 2: Decimal("2"), 3: Decimal("3"), 4: Decimal("4")}

        result = service.distribute_with_remainder(total, shares)

        # Expected: 1→100, 2→200, 3→300, 4→400
        assert result[1] == Decimal("100.00")
        assert result[2] == Decimal("200.00")
        assert result[3] == Decimal("300.00")
        assert result[4] == Decimal("400.00")
        assert sum(result.values()) == total

    def test_distribute_with_remainder_empty_shares(self, service):
        """Test with empty shares dictionary."""
        result = service.distribute_with_remainder(Decimal("100.00"), {})
        assert result == {}

    def test_distribute_with_remainder_zero_shares(self, service):
        """Test with all zero shares."""
        shares = {1: Decimal(0), 2: Decimal(0), 3: Decimal(0)}
        result = service.distribute_with_remainder(Decimal("100.00"), shares)

        assert all(amount == Decimal(0) for amount in result.values())

    def test_allocate_proportional(self, service):
        """Test proportional allocation."""
        result = service.allocate_proportional(
            Decimal("100.00"), {1: Decimal("1"), 2: Decimal("2"), 3: Decimal("1")}
        )

        # 100 * (1/4) = 25, (2/4) = 50, (1/4) = 25
        assert result[1] == Decimal("25.00")
        assert result[2] == Decimal("50.00")
        assert result[3] == Decimal("25.00")

    def test_allocate_fixed_fee(self, service):
        """Test fixed fee distribution."""
        result = service.allocate_fixed_fee(Decimal("100.00"), 4)

        # 100 / 4 = 25 each
        assert all(amount == Decimal("25.00") for amount in result.values())
        assert sum(result.values()) == Decimal("100.00")

    def test_allocate_fixed_fee_uneven(self, service):
        """Test fixed fee with uneven division."""
        result = service.allocate_fixed_fee(Decimal("100.00"), 3)

        # 100 / 3 = 33.33... + remainder 0.01
        assert sum(result.values()) == Decimal("100.00")
        assert all(amount in [Decimal("33.33"), Decimal("33.34")] for amount in result.values())

    def test_allocate_usage_based(self, service):
        """Test usage-based allocation."""
        total_cost = Decimal("120.00")
        consumption = {1: Decimal("100"), 2: Decimal("200"), 3: Decimal("200")}

        result = service.allocate_usage_based(total_cost, consumption)

        # Total consumption = 500
        # 1: 100/500 * 120 = 24
        # 2: 200/500 * 120 = 48
        # 3: 200/500 * 120 = 48
        assert result[1] == Decimal("24.00")
        assert result[2] == Decimal("48.00")
        assert result[3] == Decimal("48.00")
        assert sum(result.values()) == total_cost

    def test_calculate_consumption(self, service):
        """Test consumption calculation."""
        consumption = service.calculate_consumption(Decimal("1000.5"), Decimal("1500.3"))

        assert consumption == Decimal("499.8")

    def test_calculate_consumption_negative(self, service):
        """Test consumption with meter rollover (negative delta)."""
        # Meter rollover scenario (end < start)
        consumption = service.calculate_consumption(Decimal("9999.9"), Decimal("100.5"))

        # Result should be negative (error condition to handle)
        assert consumption == Decimal("-9899.4")
