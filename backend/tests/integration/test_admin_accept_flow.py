"""Integration tests for US3 — Admin accept/reject flow."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.telegram_user_candidate import TelegramUserCandidate
from backend.app.models.user import SOSenkiUser
from backend.app.models.admin_action import AdminAction


@pytest.fixture(scope="function")
def client(test_db_session):
    """Provide a FastAPI test client with test database."""
    return TestClient(app)


class TestAdminAcceptFlow:
    """Integration tests for admin accept flow (US3)."""

    def test_admin_accept_creates_user(self, client: TestClient, test_db_session):
        """
        T029: Admin accepts a request → new SOSenkiUser created with role.

        Flow:
        1. Create a pending TelegramUserCandidate request
        2. Admin sends POST /admin/requests/{id}/action with accept
        3. Verify SOSenkiUser is created with correct telegram_id and role
        4. Verify AdminAction audit record is created
        """
        # Step 1: Create a pending request
        request = TelegramUserCandidate(
            telegram_id=111111111,
            username="new_user",
            first_name="New",
            last_name="User",
            email="newuser@example.com",
            phone="+1111111111",
            status="pending",
        )
        test_db_session.add(request)
        test_db_session.commit()
        test_db_session.refresh(request)
        request_id = request.id

        # Step 2: Create an admin user to perform the action
        admin_user = SOSenkiUser(
            telegram_id=999999999,
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            roles=["Administrator"],
        )
        test_db_session.add(admin_user)
        test_db_session.commit()
        test_db_session.refresh(admin_user)
        admin_id = admin_user.id

        # Step 3: Admin accepts the request
        payload = {"action": "accept", "admin_id": admin_id}
        response = client.post(f"/admin/requests/{request_id}/action", json=payload)

        # Verify response
        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"

        # Step 4: Verify SOSenkiUser was created
        created_user = test_db_session.query(SOSenkiUser).filter_by(telegram_id=111111111).first()
        assert created_user is not None, "User should be created"
        assert created_user.telegram_id == 111111111
        assert created_user.email == "newuser@example.com"
        assert "user" in created_user.roles  # Default role

        # Step 5: Verify AdminAction audit record was created
        audit = (
            test_db_session.query(AdminAction)
            .filter_by(request_id=request_id, admin_id=admin_id)
            .first()
        )
        assert audit is not None, "Audit record should be created"
        assert audit.action == "accept"

        # Step 6: Verify candidate status is updated
        test_db_session.refresh(request)
        assert request.status == "accepted"

    def test_admin_accept_duplicate_telegram_id_rejected(self, client: TestClient, test_db_session):
        """
        Test: Admin cannot accept request if telegram_id already has a user.
        Expected: Returns 409 Conflict with user_already_exists error code.
        """
        telegram_id = 222222222

        # Create existing linked user
        existing_user = SOSenkiUser(
            telegram_id=telegram_id,
            email="existing@example.com",
            first_name="Existing",
            roles=["user"],
        )
        test_db_session.add(existing_user)
        test_db_session.commit()

        # Create a pending request with same telegram_id
        request = TelegramUserCandidate(
            telegram_id=telegram_id,
            username="duplicate_user",
            email="duplicate@example.com",
            status="pending",
        )
        test_db_session.add(request)
        test_db_session.commit()
        test_db_session.refresh(request)

        # Create admin user
        admin_user = SOSenkiUser(
            telegram_id=999999998,
            email="admin2@example.com",
            roles=["Administrator"],
        )
        test_db_session.add(admin_user)
        test_db_session.commit()
        test_db_session.refresh(admin_user)

        # Try to accept the request
        payload = {"action": "accept", "admin_id": admin_user.id}
        response = client.post(f"/admin/requests/{request.id}/action", json=payload)

        # Verify rejection with 409 Conflict
        assert response.status_code == 409, f"Expected 409, got {response.status_code}"
        error_data = response.json()
        assert "detail" in error_data or "error_code" in error_data

    def test_admin_reject_updates_status(self, client: TestClient, test_db_session):
        """
        Test: Admin can reject a request and status is updated to rejected.
        """
        # Create a pending request
        request = TelegramUserCandidate(
            telegram_id=333333333,
            username="reject_user",
            email="reject@example.com",
            status="pending",
        )
        test_db_session.add(request)
        test_db_session.commit()
        test_db_session.refresh(request)

        # Create admin user
        admin_user = SOSenkiUser(
            telegram_id=999999997,
            email="admin3@example.com",
            roles=["Administrator"],
        )
        test_db_session.add(admin_user)
        test_db_session.commit()
        test_db_session.refresh(admin_user)

        # Admin rejects the request
        payload = {"action": "reject", "admin_id": admin_user.id}
        response = client.post(f"/admin/requests/{request.id}/action", json=payload)

        # Verify response
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"

        # Verify status is updated
        test_db_session.refresh(request)
        assert request.status == "rejected"

        # Verify no SOSenkiUser was created
        created_user = test_db_session.query(SOSenkiUser).filter_by(telegram_id=333333333).first()
        assert created_user is None, "User should not be created on reject"

    def test_multiple_requests_independent_acceptance(self, client: TestClient, test_db_session):
        """
        Test: Multiple requests can be independently accepted.
        """
        admin_user = SOSenkiUser(
            telegram_id=999999996,
            email="admin4@example.com",
            roles=["Administrator"],
        )
        test_db_session.add(admin_user)
        test_db_session.commit()
        test_db_session.refresh(admin_user)
        admin_id = admin_user.id

        # Create two pending requests
        request1 = TelegramUserCandidate(
            telegram_id=444444444,
            username="user1",
            email="user1@example.com",
            status="pending",
        )
        request2 = TelegramUserCandidate(
            telegram_id=555555555,
            username="user2",
            email="user2@example.com",
            status="pending",
        )
        test_db_session.add(request1)
        test_db_session.add(request2)
        test_db_session.commit()
        test_db_session.refresh(request1)
        test_db_session.refresh(request2)

        # Accept both requests
        response1 = client.post(
            f"/admin/requests/{request1.id}/action", json={"action": "accept", "admin_id": admin_id}
        )
        response2 = client.post(
            f"/admin/requests/{request2.id}/action", json={"action": "accept", "admin_id": admin_id}
        )

        # Verify both succeeded
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Verify both users were created with correct telegram_ids
        user1 = test_db_session.query(SOSenkiUser).filter_by(telegram_id=444444444).first()
        user2 = test_db_session.query(SOSenkiUser).filter_by(telegram_id=555555555).first()

        assert user1 is not None and user1.email == "user1@example.com"
        assert user2 is not None and user2.email == "user2@example.com"

    def test_admin_action_requires_valid_request_id(self, client: TestClient, test_db_session):
        """
        Test: Admin action on non-existent request ID returns appropriate error.
        """
        admin_user = SOSenkiUser(
            telegram_id=999999995,
            email="admin5@example.com",
            roles=["Administrator"],
        )
        test_db_session.add(admin_user)
        test_db_session.commit()
        test_db_session.refresh(admin_user)

        # Try to accept a non-existent request
        payload = {"action": "accept", "admin_id": admin_user.id}
        response = client.post("/admin/requests/99999/action", json=payload)

        # Verify error response
        assert response.status_code == 404 or response.status_code == 400
