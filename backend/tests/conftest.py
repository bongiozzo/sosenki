"""Pytest configuration and shared fixtures for backend tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Create test engine BEFORE importing app
test_engine = create_engine(
    "sqlite:///:memory:",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)

# Patch database module before importing app
import backend.app.database as db_module

original_engine = db_module.engine
db_module.engine = test_engine

# Now import the app and models
from backend.app.database import Base
from backend.app.main import app


@pytest.fixture(scope="function")
def test_db_session():
    """Provide a test database session with all tables created."""
    # Create all tables before each test
    Base.metadata.create_all(bind=test_engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()

    # Monkey-patch the get_db dependency
    from backend.app.database import get_db

    def override_get_db():
        """Override get_db to use test session."""
        # Ensure tables exist every time (in case first request initializes them)
        Base.metadata.create_all(bind=test_engine)
        try:
            yield session
        finally:
            pass  # Don't close, let fixture handle cleanup

    app.dependency_overrides[get_db] = override_get_db

    yield session

    session.close()
    app.dependency_overrides.clear()

    # Clean up tables after each test
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(test_db_session):
    """Provide a FastAPI test client with test database."""
    return TestClient(app)


@pytest.fixture
def test_telegram_id() -> int:
    """Provide a test Telegram ID."""
    return 123456789


@pytest.fixture
def test_init_data() -> dict:
    """Provide sample initData from Telegram Web App (not cryptographically valid, for test only)."""
    return {
        "user": {
            "id": 123456789,
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser",
            "language_code": "en",
            "is_premium": False,
        },
        "auth_date": 1730629500,
        "hash": "test_hash_not_validated_in_unit_tests",
    }
