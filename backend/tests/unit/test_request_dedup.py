"""Unit tests for request deduplication logic (US2)."""

import pytest
from backend.app.services.request_service import create_request, DuplicateRequestError
from backend.app.models.telegram_user_candidate import TelegramUserCandidate


class TestRequestDedup:
    """Unit tests for request creation and deduplication."""

    def test_create_request_success(self, test_db_session):
        """create_request successfully creates a TelegramUserCandidate record."""
        candidate = create_request(
            db=test_db_session,
            telegram_id=123456789,
            username="test_user",
            first_name="John",
            last_name="Doe",
            phone="+1234567890",
            email="john@example.com",
        )
        assert candidate.id is not None
        assert candidate.telegram_id == 123456789
        assert candidate.username == "test_user"
        assert candidate.status == "pending"

    def test_create_request_duplicate_raises_error(self, test_db_session):
        """create_request raises DuplicateRequestError when telegram_id already exists."""
        # Create first request
        create_request(
            db=test_db_session,
            telegram_id=987654321,
            username="alice",
            first_name="Alice",
            last_name="Smith",
            phone="+1111111111",
            email="alice@example.com",
        )

        # Try to create duplicate
        with pytest.raises(DuplicateRequestError):
            create_request(
                db=test_db_session,
                telegram_id=987654321,  # Same telegram_id
                username="alice_new",
                first_name="Alice",
                last_name="Smith",
                phone="+2222222222",
                email="alice_new@example.com",
            )

    def test_create_request_different_telegram_ids_succeeds(self, test_db_session):
        """create_request succeeds for different telegram_ids."""
        candidate1 = create_request(
            db=test_db_session,
            telegram_id=111111111,
            username="user1",
            first_name="User",
            last_name="One",
            phone="+1111111111",
            email="user1@example.com",
        )
        candidate2 = create_request(
            db=test_db_session,
            telegram_id=222222222,
            username="user2",
            first_name="User",
            last_name="Two",
            phone="+2222222222",
            email="user2@example.com",
        )
        assert candidate1.id != candidate2.id
        assert candidate1.telegram_id == 111111111
        assert candidate2.telegram_id == 222222222

    def test_create_request_persists_to_db(self, test_db_session):
        """create_request persists the candidate to the database."""
        telegram_id = 333333333
        create_request(
            db=test_db_session,
            telegram_id=telegram_id,
            username="persist_test",
            first_name="Persist",
            last_name="Test",
            phone="+3333333333",
            email="persist@example.com",
        )

        # Query the database to verify it was persisted
        candidate = (
            test_db_session.query(TelegramUserCandidate).filter_by(telegram_id=telegram_id).first()
        )
        assert candidate is not None
        assert candidate.username == "persist_test"
