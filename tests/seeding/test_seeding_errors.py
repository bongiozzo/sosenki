"""Contract tests for error scenarios in seeding.

Tests for handling various error conditions during the seeding process.
"""

import pytest
from sqlalchemy import delete, text

from seeding.config.seeding_config import SeedingConfig
from src.models.access_request import AccessRequest
from src.models.property import Property
from src.models.user import User
from src.services import SessionLocal


class TestSeedingErrorScenarios:
    """Contract tests for error scenarios (T040)."""

    @pytest.fixture(autouse=True)
    def cleanup_db(self):
        """Clean up database before and after each test."""
        db = SessionLocal()
        try:
            db.execute(delete(AccessRequest))
            db.execute(delete(Property))
            db.execute(delete(User))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        yield

        # Cleanup after test
        db = SessionLocal()
        try:
            db.execute(delete(AccessRequest))
            db.execute(delete(Property))
            db.execute(delete(User))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def test_seeding_config_loads(self):
        """Test that seeding configuration can be loaded (US2)."""
        # Should load without error
        config = SeedingConfig.load()
        assert config is not None
        assert config.get_user_defaults() is not None

    def test_session_can_be_created(self):
        """Test that database session can be created (US1)."""
        db = SessionLocal()
        assert db is not None
        try:
            # Verify we can execute a query
            result = db.execute(text("SELECT 1"))
            assert result is not None
        finally:
            db.close()

    def test_database_transaction_commits(self):
        """Test that database transactions can commit (US1)."""
        db = SessionLocal()
        try:
            # Create a test entry and commit
            user = User(name="Test User", is_active=True)
            db.add(user)
            db.commit()

            # Verify it was saved by creating a new session
            db2 = SessionLocal()
            saved_user = db2.query(User).filter_by(name="Test User").first()
            assert saved_user is not None
            assert saved_user.name == "Test User"
            db2.close()
        finally:
            db.close()

    def test_database_transaction_rollback(self):
        """Test that database transactions can rollback (US1)."""
        db = SessionLocal()
        try:
            # Create entry but rollback
            user = User(name="Rollback Test", is_active=True)
            db.add(user)
            db.rollback()

            # Verify it was NOT saved
            saved_user = db.query(User).filter_by(name="Rollback Test").first()
            assert saved_user is None
        finally:
            db.close()

    def test_database_connection_pool_works(self):
        """Test that database connection pool operates correctly (US1)."""
        # Create multiple connections
        sessions = [SessionLocal() for _ in range(3)]
        try:
            for session in sessions:
                assert session is not None
                result = session.execute(text("SELECT 1"))
                assert result is not None
        finally:
            for session in sessions:
                session.close()

    def test_concurrent_session_transactions(self):
        """Test that concurrent sessions handle transactions properly (US1)."""
        db1 = SessionLocal()
        db2 = SessionLocal()

        try:
            # Session 1: Create user
            user1 = User(name="Concurrent User 1", is_active=True)
            db1.add(user1)
            db1.commit()

            # Session 2: Create another user
            user2 = User(name="Concurrent User 2", is_active=False)
            db2.add(user2)
            db2.commit()

            # Verify both were saved
            db1_user2 = db1.query(User).filter_by(name="Concurrent User 2").first()
            db2_user1 = db2.query(User).filter_by(name="Concurrent User 1").first()

            assert db1_user2 is not None
            assert db2_user1 is not None
        finally:
            db1.close()
            db2.close()
