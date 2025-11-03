"""Unit tests for admin action audit creation (US3)."""

import pytest
from backend.app.services.admin_service import (
    accept_request,
    reject_request,
    UserAlreadyExistsError,
)
from backend.app.models.admin_action import AdminAction
from backend.app.models.user import SOSenkiUser
from backend.app.models.telegram_user_candidate import TelegramUserCandidate


class TestAdminActionAudit:
    """Unit tests for admin action and audit creation."""

    def test_accept_request_creates_user(self, test_db_session):
        """accept_request creates a SOSenkiUser with telegram_id."""
        # Create a candidate request
        candidate = TelegramUserCandidate(
            telegram_id=111111111,
            username="test_user",
            first_name="Test",
            last_name="User",
            phone="+1111111111",
            email="test@example.com",
            status="pending",
        )
        test_db_session.add(candidate)
        test_db_session.commit()

        # Admin accepts the request
        admin_id = 1
        user = accept_request(
            db=test_db_session,
            request_id=candidate.id,
            admin_id=admin_id,
        )

        assert user.telegram_id == 111111111
        assert user.username == "test_user"

    def test_accept_request_creates_audit_record(self, test_db_session):
        """accept_request creates an AdminAction audit record."""
        # Create a candidate request
        candidate = TelegramUserCandidate(
            telegram_id=222222222,
            username="alice",
            first_name="Alice",
            last_name="Smith",
            phone="+2222222222",
            email="alice@example.com",
            status="pending",
        )
        test_db_session.add(candidate)
        test_db_session.commit()

        # Admin accepts the request
        admin_id = 42
        accept_request(
            db=test_db_session,
            request_id=candidate.id,
            admin_id=admin_id,
        )

        # Verify audit record exists
        audit = (
            test_db_session.query(AdminAction)
            .filter_by(admin_id=admin_id, request_id=candidate.id)
            .first()
        )
        assert audit is not None
        assert audit.action == "accept"

    def test_accept_request_duplicate_telegram_id_raises_error(self, test_db_session):
        """accept_request raises UserAlreadyExistsError if telegram_id already in SOSenkiUser."""
        # Create an existing user
        existing_user = SOSenkiUser(
            telegram_id=333333333,
            username="existing",
        )
        test_db_session.add(existing_user)
        test_db_session.commit()

        # Create a candidate with same telegram_id
        candidate = TelegramUserCandidate(
            telegram_id=333333333,
            username="new_user",
            first_name="New",
            last_name="User",
            phone="+3333333333",
            email="new@example.com",
            status="pending",
        )
        test_db_session.add(candidate)
        test_db_session.commit()

        # Try to accept (should fail due to duplicate telegram_id)
        with pytest.raises(UserAlreadyExistsError):
            accept_request(
                db=test_db_session,
                request_id=candidate.id,
                admin_id=1,
            )

    def test_reject_request_updates_status(self, test_db_session):
        """reject_request updates candidate status to rejected."""
        # Create a candidate request
        candidate = TelegramUserCandidate(
            telegram_id=444444444,
            username="bob",
            first_name="Bob",
            last_name="Jones",
            phone="+4444444444",
            email="bob@example.com",
            status="pending",
        )
        test_db_session.add(candidate)
        test_db_session.commit()

        # Admin rejects the request
        admin_id = 5
        reject_request(
            db=test_db_session,
            request_id=candidate.id,
            admin_id=admin_id,
            reason="Not qualified",
        )

        # Verify candidate status is updated
        updated_candidate = (
            test_db_session.query(TelegramUserCandidate).filter_by(id=candidate.id).first()
        )
        assert updated_candidate.status == "rejected"

    def test_reject_request_creates_audit_record(self, test_db_session):
        """reject_request creates an AdminAction audit record."""
        # Create a candidate request
        candidate = TelegramUserCandidate(
            telegram_id=555555555,
            username="charlie",
            first_name="Charlie",
            last_name="Brown",
            phone="+5555555555",
            email="charlie@example.com",
            status="pending",
        )
        test_db_session.add(candidate)
        test_db_session.commit()

        # Admin rejects the request
        admin_id = 10
        reason = "Does not meet requirements"
        reject_request(
            db=test_db_session,
            request_id=candidate.id,
            admin_id=admin_id,
            reason=reason,
        )

        # Verify audit record with reason
        audit = (
            test_db_session.query(AdminAction)
            .filter_by(admin_id=admin_id, request_id=candidate.id)
            .first()
        )
        assert audit is not None
        assert audit.action == "reject"
        assert audit.reason == reason
