"""Integration tests for meter readings and usage-based billing."""

import pytest
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base
from src.services.payment_service import PaymentService
from src.services.allocation_service import AllocationService


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestMeterReadingManagement:
    """Test meter reading CRUD operations."""

    def test_record_meter_reading(self, db_session):
        """Test recording a meter reading."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        reading = service.record_meter_reading(
            period_id=period.id,
            meter_name="Water Meter A",
            meter_start_reading=Decimal("1000.0"),
            meter_end_reading=Decimal("1150.5"),
            calculated_total_cost=Decimal("750.00"),
            unit="m³"
        )
        
        assert reading.id is not None
        assert reading.meter_name == "Water Meter A"
        assert reading.meter_start_reading == Decimal("1000.0")
        assert reading.meter_end_reading == Decimal("1150.5")
        assert reading.calculated_total_cost == Decimal("750.00")
        assert reading.unit == "m³"

    def test_record_multiple_meter_readings(self, db_session):
        """Test recording multiple meter readings for different meters."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record water meter
        water_reading = service.record_meter_reading(
            period_id=period.id,
            meter_name="Water Meter",
            meter_start_reading=Decimal("1000.0"),
            meter_end_reading=Decimal("1150.0"),
            calculated_total_cost=Decimal("750.00"),
            unit="m³"
        )
        
        # Record electric meter
        electric_reading = service.record_meter_reading(
            period_id=period.id,
            meter_name="Electric Meter",
            meter_start_reading=Decimal("5000.0"),
            meter_end_reading=Decimal("5300.0"),
            calculated_total_cost=Decimal("1500.00"),
            unit="kWh"
        )
        
        readings = service.get_meter_readings(period.id)
        assert len(readings) == 2
        assert any(r.meter_name == "Water Meter" for r in readings)
        assert any(r.meter_name == "Electric Meter" for r in readings)

    def test_get_meter_reading_by_id(self, db_session):
        """Test retrieving a specific meter reading."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        created = service.record_meter_reading(
            period_id=period.id,
            meter_name="Water Meter",
            meter_start_reading=Decimal("1000.0"),
            meter_end_reading=Decimal("1150.0"),
            calculated_total_cost=Decimal("750.00")
        )
        
        retrieved = service.get_meter_reading(created.id)
        assert retrieved.id == created.id
        assert retrieved.meter_name == "Water Meter"

    def test_meter_reading_with_description(self, db_session):
        """Test meter reading with optional description."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        reading = service.record_meter_reading(
            period_id=period.id,
            meter_name="Water Meter",
            meter_start_reading=Decimal("1000.0"),
            meter_end_reading=Decimal("1150.0"),
            calculated_total_cost=Decimal("750.00"),
            description="Q4 water consumption with meter replacement"
        )
        
        assert reading.description == "Q4 water consumption with meter replacement"

    def test_meter_reading_zero_cost(self, db_session):
        """Test meter reading with zero cost (valid case)."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        reading = service.record_meter_reading(
            period_id=period.id,
            meter_name="Water Meter",
            meter_start_reading=Decimal("1000.0"),
            meter_end_reading=Decimal("1000.0"),  # No consumption
            calculated_total_cost=Decimal("0.00")
        )
        
        assert reading.calculated_total_cost == Decimal("0.00")

    def test_meter_reading_validation_negative_cost(self, db_session):
        """Test validation rejects negative calculated cost."""
        service = PaymentService(db=db_session)
        
        period = service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        with pytest.raises(ValueError, match="must be non-negative"):
            service.record_meter_reading(
                period_id=period.id,
                meter_name="Water Meter",
                meter_start_reading=Decimal("1000.0"),
                meter_end_reading=Decimal("1150.0"),
                calculated_total_cost=Decimal("-100.00")
            )

    def test_meter_reading_invalid_period(self, db_session):
        """Test validation rejects invalid period."""
        service = PaymentService(db=db_session)
        
        with pytest.raises(ValueError, match="not found"):
            service.record_meter_reading(
                period_id=9999,
                meter_name="Water Meter",
                meter_start_reading=Decimal("1000.0"),
                meter_end_reading=Decimal("1150.0"),
                calculated_total_cost=Decimal("750.00")
            )


class TestConsumptionCalculation:
    """Test consumption calculation from meter readings."""

    def test_calculate_consumption_normal(self):
        """Test normal consumption calculation."""
        service = PaymentService(db=None)
        
        consumption = service.calculate_consumption(
            start_reading=Decimal("1000.0"),
            end_reading=Decimal("1150.5")
        )
        
        assert consumption == Decimal("150.5")

    def test_calculate_consumption_zero(self):
        """Test consumption when readings are equal."""
        service = PaymentService(db=None)
        
        consumption = service.calculate_consumption(
            start_reading=Decimal("1000.0"),
            end_reading=Decimal("1000.0")
        )
        
        assert consumption == Decimal("0")

    def test_calculate_consumption_meter_rollover(self):
        """Test consumption with meter rollover (negative value)."""
        service = PaymentService(db=None)
        
        # Meter rolls over from 9999 to 0
        consumption = service.calculate_consumption(
            start_reading=Decimal("9900.0"),
            end_reading=Decimal("100.0")
        )
        
        assert consumption == Decimal("-9800.0")

    def test_calculate_consumption_decimal_precision(self):
        """Test consumption calculation with high precision decimals."""
        service = PaymentService(db=None)
        
        consumption = service.calculate_consumption(
            start_reading=Decimal("1000.123"),
            end_reading=Decimal("1200.456")
        )
        
        assert consumption == Decimal("200.333")


class TestUsageBasedAllocation:
    """Test usage-based allocation integrated with meter readings."""

    def test_allocate_by_consumption(self, db_session):
        """Test allocation by meter consumption."""
        allocation_service = AllocationService()
        
        total_cost = Decimal("1500.00")
        
        # Consumption by property
        consumption = {
            1: Decimal("100"),  # Property 1: 100 units (25%)
            2: Decimal("200"),  # Property 2: 200 units (50%)
            3: Decimal("100"),  # Property 3: 100 units (25%)
        }
        
        allocation = allocation_service.allocate_usage_based(total_cost, consumption)
        
        assert allocation[1] == Decimal("375.00")  # 25%
        assert allocation[2] == Decimal("750.00")  # 50%
        assert allocation[3] == Decimal("375.00")  # 25%
        assert sum(allocation.values()) == total_cost

    def test_usage_based_allocation_zero_consumption(self):
        """Test allocation when some properties have zero consumption."""
        allocation_service = AllocationService()
        
        total_cost = Decimal("1000.00")
        consumption = {
            1: Decimal("0"),     # Property 1: no consumption
            2: Decimal("200"),   # Property 2: all consumption
        }
        
        allocation = allocation_service.allocate_usage_based(total_cost, consumption)
        
        assert allocation[1] == Decimal("0.00")
        assert allocation[2] == Decimal("1000.00")

    def test_usage_based_allocation_uneven_split(self):
        """Test allocation with uneven consumption split."""
        allocation_service = AllocationService()
        
        total_cost = Decimal("333.33")
        consumption = {
            1: Decimal("1"),
            2: Decimal("2"),
            3: Decimal("7"),
        }
        
        allocation = allocation_service.allocate_usage_based(total_cost, consumption)
        
        # Sum should be preserved
        assert sum(allocation.values()) == total_cost
        
        # Ratios should reflect consumption (1:2:7)
        assert allocation[1] < allocation[2]
        assert allocation[2] < allocation[3]

    def test_end_to_end_meter_to_allocation(self, db_session):
        """Test end-to-end flow from meter reading to allocation."""
        payment_service = PaymentService(db=db_session)
        allocation_service = AllocationService()
        
        # Create period
        period = payment_service.create_period(
            name="Nov 2025",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30)
        )
        
        # Record meter reading
        reading = payment_service.record_meter_reading(
            period_id=period.id,
            meter_name="Water Meter",
            meter_start_reading=Decimal("1000.0"),
            meter_end_reading=Decimal("1300.0"),
            calculated_total_cost=Decimal("1500.00"),
            unit="m³"
        )
        
        # Calculate consumption from reading
        consumption = payment_service.calculate_consumption(
            reading.meter_start_reading,
            reading.meter_end_reading
        )
        
        assert consumption == Decimal("300.0")
        
        # Now allocate by owner consumption (assuming they consumed proportionally)
        owner_consumption = {
            1: Decimal("100"),  # 33.33%
            2: Decimal("100"),  # 33.33%
            3: Decimal("100"),  # 33.33%
        }
        
        allocation = allocation_service.allocate_usage_based(
            reading.calculated_total_cost,
            owner_consumption
        )
        
        # Each should get ~500
        assert allocation[1] == Decimal("500.00")
        assert allocation[2] == Decimal("500.00")
        assert allocation[3] == Decimal("500.00")
        assert sum(allocation.values()) == reading.calculated_total_cost
