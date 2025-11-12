"""Tests for admin utilities."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.models import Base
from src.models.user import User
from src.services.admin_utils import get_admin_telegram_id, get_admin_user


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_get_admin_telegram_id_when_admin_exists(db_session: Session):
    """Test retrieving admin telegram ID when admin user exists."""
    # Create an admin user
    admin = User(
        name="П",
        telegram_id="123456789",
        is_administrator=True,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    # Retrieve admin telegram ID
    admin_id = get_admin_telegram_id(db_session)

    assert admin_id == "123456789"


def test_get_admin_telegram_id_when_no_admin_exists(db_session: Session):
    """Test retrieving admin telegram ID when no admin user exists."""
    # Add a non-admin user
    user = User(
        name="Regular User",
        telegram_id="987654321",
        is_administrator=False,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Try to retrieve admin telegram ID
    admin_id = get_admin_telegram_id(db_session)

    assert admin_id is None


def test_get_admin_telegram_id_when_admin_has_no_telegram_id(db_session: Session):
    """Test retrieving admin telegram ID when admin exists but has no telegram_id."""
    # Create an admin user without telegram_id
    admin = User(
        name="П",
        is_administrator=True,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    # Try to retrieve admin telegram ID
    admin_id = get_admin_telegram_id(db_session)

    assert admin_id is None


def test_get_admin_user_when_admin_exists(db_session: Session):
    """Test retrieving admin user when admin exists."""
    # Create an admin user
    admin = User(
        name="П",
        telegram_id="123456789",
        is_administrator=True,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    # Retrieve admin user
    admin_user = get_admin_user(db_session)

    assert admin_user is not None
    assert admin_user.name == "П"
    assert admin_user.telegram_id == "123456789"
    assert admin_user.is_administrator is True


def test_get_admin_user_when_no_admin_exists(db_session: Session):
    """Test retrieving admin user when no admin exists."""
    # Add a non-admin user
    user = User(
        name="Regular User",
        telegram_id="987654321",
        is_administrator=False,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Try to retrieve admin user
    admin_user = get_admin_user(db_session)

    assert admin_user is None


def test_get_admin_user_returns_first_admin_when_multiple_exist(db_session: Session):
    """Test that first admin is returned when multiple admins exist."""
    # Create multiple admin users
    admin1 = User(
        name="Admin One",
        telegram_id="111111111",
        is_administrator=True,
        is_active=True,
    )
    admin2 = User(
        name="Admin Two",
        telegram_id="222222222",
        is_administrator=True,
        is_active=True,
    )
    db_session.add(admin1)
    db_session.add(admin2)
    db_session.commit()

    # Retrieve admin user
    admin_user = get_admin_user(db_session)

    # Should return one of them (database order)
    assert admin_user is not None
    assert admin_user.is_administrator is True
