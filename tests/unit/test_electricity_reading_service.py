"""Unit tests for ElectricityReadingService."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.electricity_reading import ElectricityReading
from src.models.property import Property
from src.services.electricity_reading_service import ElectricityReadingService


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()  # Changed to AsyncMock for await support
    return session


@pytest.fixture
def sample_property():
    """Create a sample property for testing."""
    prop = Property(
        id=1,
        owner_id=1,
        property_name="Test Property",
        type="Apartment",
        share_weight=Decimal("1.0"),
        is_active=True,
    )
    return prop


@pytest.fixture
def sample_reading():
    """Create a sample electricity reading."""
    reading = ElectricityReading(
        id=1,
        property_id=1,
        reading_value=Decimal("1000.50"),
        reading_date=date(2025, 1, 1),
    )
    return reading


class TestGetPropertiesWithLatestReadings:
    """Tests for get_properties_with_latest_readings method."""

    @pytest.mark.asyncio
    async def test_get_properties_with_readings(self, mock_session):
        """Test getting properties with their latest readings."""
        # Mock properties
        property_a = Property(id=1, property_name="Property A", is_active=True)
        property_b = Property(id=2, property_name="Property B", is_active=True)

        # Mock latest readings
        reading_a = ElectricityReading(
            id=1, property_id=1, reading_value=Decimal("1500.0"), reading_date=date(2025, 1, 15)
        )
        reading_b = ElectricityReading(
            id=2, property_id=2, reading_value=Decimal("2000.0"), reading_date=date(2025, 1, 10)
        )

        # Mock execute for properties query
        mock_props_result = MagicMock()
        mock_props_result.scalars.return_value.all.return_value = [property_a, property_b]

        # Mock execute for latest readings queries
        mock_reading_a = MagicMock()
        mock_reading_a.scalar_one_or_none.return_value = reading_a
        mock_reading_b = MagicMock()
        mock_reading_b.scalar_one_or_none.return_value = reading_b

        # Set up execute mock to return different results for each call
        mock_session.execute = AsyncMock(
            side_effect=[mock_props_result, mock_reading_a, mock_reading_b]
        )

        service = ElectricityReadingService(mock_session)
        result = await service.get_properties_with_latest_readings()

        assert len(result) == 2
        assert result[0][0].property_name == "Property A"
        assert result[0][1].reading_value == Decimal("1500.0")
        assert result[1][0].property_name == "Property B"
        assert result[1][1].reading_value == Decimal("2000.0")

    @pytest.mark.asyncio
    async def test_get_properties_no_readings(self, mock_session):
        """Test getting properties when no readings exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ElectricityReadingService(mock_session)
        result = await service.get_properties_with_latest_readings()

        assert result == []


class TestGetReadingById:
    """Tests for get_reading_by_id method."""

    @pytest.mark.asyncio
    async def test_get_existing_reading(self, mock_session, sample_reading):
        """Test getting an existing reading by ID."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_reading

        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ElectricityReadingService(mock_session)
        result = await service.get_reading_by_id(1)

        assert result == sample_reading
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_get_nonexistent_reading(self, mock_session):
        """Test getting a non-existent reading returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ElectricityReadingService(mock_session)
        result = await service.get_reading_by_id(999)

        assert result is None


class TestGetLatestReadingForProperty:
    """Tests for get_latest_reading_for_property method."""

    @pytest.mark.asyncio
    async def test_get_latest_reading(self, mock_session, sample_reading):
        """Test getting the latest reading for a property."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_reading

        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ElectricityReadingService(mock_session)
        result = await service.get_latest_reading_for_property(1)

        assert result == sample_reading

    @pytest.mark.asyncio
    async def test_get_latest_reading_none_exists(self, mock_session):
        """Test getting latest reading when none exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ElectricityReadingService(mock_session)
        result = await service.get_latest_reading_for_property(1)

        assert result is None


class TestCreateReading:
    """Tests for create_reading method."""

    @pytest.mark.asyncio
    async def test_create_reading_success(self, mock_session):
        """Test successful creation of a reading."""
        # Mock get_latest_reading_for_property to return None (no previous reading)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        service = ElectricityReadingService(mock_session)
        result = await service.create_reading(
            property_id=1,
            reading_date=date(2025, 1, 15),
            reading_value=Decimal("1500.0"),
            actor_id=1,
        )

        assert result.property_id == 1
        assert result.reading_value == Decimal("1500.0")
        assert result.reading_date == date(2025, 1, 15)
        assert mock_session.add.call_count == 2  # ElectricityReading + AuditLog

    @pytest.mark.asyncio
    async def test_create_reading_validates_positive_value(self, mock_session):
        """Test that create_reading validates positive reading value."""
        service = ElectricityReadingService(mock_session)

        with pytest.raises(ValueError, match="Reading value must be positive"):
            await service.create_reading(
                property_id=1,
                reading_date=date(2025, 1, 15),
                reading_value=Decimal("-100.0"),
                actor_id=1,
            )

    @pytest.mark.asyncio
    async def test_create_reading_validates_greater_than_previous(self, mock_session):
        """Test that new reading must be greater than previous reading."""
        # Mock previous reading
        previous_reading = ElectricityReading(
            id=1,
            property_id=1,
            reading_value=Decimal("2000.0"),
            reading_date=date(2025, 1, 1),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = previous_reading
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ElectricityReadingService(mock_session)

        with pytest.raises(ValueError, match="must be greater than or equal to previous reading"):
            await service.create_reading(
                property_id=1,
                reading_date=date(2025, 1, 15),
                reading_value=Decimal("1500.0"),  # Less than previous 2000.0
                actor_id=1,
            )


class TestUpdateReading:
    """Tests for update_reading method."""

    @pytest.mark.asyncio
    async def test_update_reading_success(self, mock_session, sample_reading):
        """Test successful update of a reading."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_reading
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ElectricityReadingService(mock_session)

        result = await service.update_reading(
            reading_id=1,
            reading_date=date(2025, 1, 20),
            reading_value=Decimal("1600.0"),
            actor_id=1,
        )

        assert result.reading_date == date(2025, 1, 20)
        assert result.reading_value == Decimal("1600.0")
        assert mock_session.add.call_count == 1  # AuditLog only

    @pytest.mark.asyncio
    async def test_update_reading_not_found(self, mock_session):
        """Test update when reading doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ElectricityReadingService(mock_session)

        with pytest.raises(ValueError, match="Reading with ID 999 not found"):
            await service.update_reading(
                reading_id=999,
                reading_date=date(2025, 1, 20),
                reading_value=Decimal("1600.0"),
                actor_id=1,
            )

    @pytest.mark.asyncio
    async def test_update_reading_validates_positive_value(self, mock_session, sample_reading):
        """Test that update_reading validates positive reading value."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_reading
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ElectricityReadingService(mock_session)

        with pytest.raises(ValueError, match="Reading value must be positive"):
            await service.update_reading(
                reading_id=1,
                reading_date=date(2025, 1, 20),
                reading_value=Decimal("-100.0"),
                actor_id=1,
            )


class TestDeleteReading:
    """Tests for delete_reading method."""

    @pytest.mark.asyncio
    async def test_delete_reading_success(self, mock_session, sample_reading):
        """Test successful deletion of a reading."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_reading
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ElectricityReadingService(mock_session)
        await service.delete_reading(reading_id=1, actor_id=1)

        mock_session.delete.assert_called_once_with(sample_reading)
        assert mock_session.add.call_count == 1  # AuditLog only

    @pytest.mark.asyncio
    async def test_delete_reading_not_found(self, mock_session):
        """Test delete when reading doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ElectricityReadingService(mock_session)

        with pytest.raises(ValueError, match="Reading with ID 999 not found"):
            await service.delete_reading(reading_id=999, actor_id=1)
