"""Unit tests for period_service.py."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base
from src.models.account import Account
from src.models.service_period import ServicePeriod
from src.models.user import User
from src.services.period_service import PeriodDefaults, ServicePeriodService


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def admin_user(db_session):
    """Create admin user for tests."""
    user = User(telegram_id=123, is_active=True, is_administrator=True)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def account(db_session, admin_user):
    """Create account for tests."""
    acc = Account(user_id=admin_user.id, name="Test Account")
    db_session.add(acc)
    db_session.commit()
    return acc


def test_period_service_get_open_periods(db_session):
    """Test getting open periods."""
    # Create some test periods
    period1 = ServicePeriod(
        start_date=date(2025, 1, 1), end_date=date(2025, 1, 31), name="Period 1", status="open"
    )
    period2 = ServicePeriod(
        start_date=date(2025, 2, 1), end_date=date(2025, 2, 28), name="Period 2", status="open"
    )
    period3 = ServicePeriod(
        start_date=date(2024, 12, 1),
        end_date=date(2024, 12, 31),
        name="Period 3",
        status="closed",
    )
    db_session.add_all([period1, period2, period3])
    db_session.commit()

    service = ServicePeriodService(db_session)
    open_periods = service.get_open_periods()

    assert len(open_periods) == 2
    assert all(p.status == "open" for p in open_periods)


def test_period_service_get_open_periods_limit(db_session):
    """Test getting open periods with limit."""
    # Create 5 open periods
    for i in range(5):
        period = ServicePeriod(
            start_date=date(2025, i + 1, 1),
            end_date=date(2025, i + 1, 28),
            name=f"Period {i}",
            status="open",
        )
        db_session.add(period)
    db_session.commit()

    service = ServicePeriodService(db_session)
    periods = service.get_open_periods(limit=3)

    assert len(periods) == 3


def test_period_service_get_by_id(db_session):
    """Test getting period by id."""
    period = ServicePeriod(
        start_date=date(2025, 1, 1), end_date=date(2025, 1, 31), name="Test Period", status="open"
    )
    db_session.add(period)
    db_session.commit()

    service = ServicePeriodService(db_session)
    retrieved = service.get_by_id(period.id)

    assert retrieved is not None
    assert retrieved.id == period.id
    assert retrieved.name == "Test Period"


def test_period_service_get_by_id_not_found(db_session):
    """Test getting non-existent period."""
    service = ServicePeriodService(db_session)
    result = service.get_by_id(999)

    assert result is None


def test_period_service_get_latest_period(db_session):
    """Test getting latest period."""
    period1 = ServicePeriod(
        start_date=date(2025, 1, 1), end_date=date(2025, 1, 31), name="Period 1", status="open"
    )
    period2 = ServicePeriod(
        start_date=date(2025, 2, 1), end_date=date(2025, 2, 28), name="Period 2", status="open"
    )
    db_session.add_all([period1, period2])
    db_session.commit()

    service = ServicePeriodService(db_session)
    latest = service.get_latest_period()

    assert latest is not None
    assert latest.name == "Period 2"


def test_period_service_get_latest_period_none(db_session):
    """Test getting latest period when none exist."""
    service = ServicePeriodService(db_session)
    result = service.get_latest_period()

    assert result is None


def test_period_service_get_previous_period_defaults(db_session):
    """Test getting previous period defaults."""
    # Create previous period with electricity data
    # The method looks for end_date == current_start_date
    prev_period = ServicePeriod(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 2, 1),  # This should match the start date we query with
        name="Previous",
        status="closed",
        electricity_end=Decimal("200"),
        electricity_multiplier=Decimal("1.5"),
        electricity_rate=Decimal("5.50"),
        electricity_losses=Decimal("0.2"),
    )
    db_session.add(prev_period)
    db_session.commit()

    service = ServicePeriodService(db_session)
    # Pass the same date as the previous period's end_date
    defaults = service.get_previous_period_defaults(date(2025, 2, 1))

    assert defaults is not None
    # Decimal("200") converts to "200" but might have decimal places in string form
    assert "200" in defaults.electricity_end
    assert "1.5" in defaults.electricity_multiplier
    assert "5.5" in defaults.electricity_rate
    assert "0.2" in defaults.electricity_losses


def test_period_service_get_previous_period_defaults_none(db_session):
    """Test getting defaults when no previous period exists."""
    service = ServicePeriodService(db_session)
    result = service.get_previous_period_defaults(date(2025, 2, 1))

    # Should return empty PeriodDefaults, not None
    assert result is not None
    assert result.electricity_end is None
    assert result.electricity_multiplier is None
    assert result.electricity_rate is None
    assert result.electricity_losses is None


def test_period_service_list_periods(db_session):
    """Test listing periods."""
    period1 = ServicePeriod(
        start_date=date(2025, 1, 1), end_date=date(2025, 1, 31), name="P1", status="open"
    )
    period2 = ServicePeriod(
        start_date=date(2025, 2, 1), end_date=date(2025, 2, 28), name="P2", status="closed"
    )
    db_session.add_all([period1, period2])
    db_session.commit()

    service = ServicePeriodService(db_session)
    periods = service.list_periods()

    assert len(periods) == 2


def test_period_service_list_periods_limit(db_session):
    """Test listing periods with limit."""
    for i in range(5):
        period = ServicePeriod(
            start_date=date(2025, i + 1, 1),
            end_date=date(2025, i + 1, 28),
            name=f"P{i}",
            status="open",
        )
        db_session.add(period)
    db_session.commit()

    service = ServicePeriodService(db_session)
    periods = service.list_periods(limit=2)

    assert len(periods) == 2


def test_period_defaults_dataclass():
    """Test PeriodDefaults dataclass."""
    defaults = PeriodDefaults(
        electricity_end="200",
        electricity_multiplier="1.5",
        electricity_rate="5.50",
        electricity_losses="0.2",
    )

    assert defaults.electricity_end == "200"
    assert defaults.electricity_multiplier == "1.5"
    assert defaults.electricity_rate == "5.50"
    assert defaults.electricity_losses == "0.2"
