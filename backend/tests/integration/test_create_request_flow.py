"""
Integration tests for POST /requests flow.

Tests the complete flow:
1. Frontend calls POST /requests with unlinked user data
2. Request is created in database
3. Admin is notified via telegram_bot service
4. Response contains request details with 201 status
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.telegram_user_candidate import TelegramUserCandidate
from backend.app.services.telegram_bot import get_telegram_bot_service, MockTransport


class TestCreateRequestFlow:
    """Integration tests for request creation and admin notification."""

    def test_create_request_persists_to_database(
        self, client: TestClient, test_db_session: Session
    ):
        """POST /requests creates a TelegramUserCandidate record in database."""
        response = client.post(
            "/requests",
            json={
                "telegram_id": 111111111,
                "first_name": "Alice",
                "last_name": "Smith",
                "telegram_username": "alice_smith",
                "note": "I want to join!",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["telegram_id"] == 111111111

        # Verify database record exists
        candidate = (
            test_db_session.query(TelegramUserCandidate).filter_by(telegram_id=111111111).first()
        )
        assert candidate is not None
        assert candidate.first_name == "Alice"
        assert candidate.last_name == "Smith"
        assert candidate.status == "pending"

    def test_create_request_notifies_admin(self, client: TestClient, test_db_session: Session):
        """POST /requests triggers admin notification via telegram_bot service."""
        # Get the mock transport to verify notifications
        bot_service = get_telegram_bot_service()
        assert isinstance(bot_service.transport, MockTransport), "Test must use mock transport"
        mock_transport = bot_service.transport
        mock_transport.clear()

        response = client.post(
            "/requests",
            json={
                "telegram_id": 222222222,
                "first_name": "Bob",
                "last_name": "Jones",
                "telegram_username": "bob_jones",
                "note": "Please approve me",
            },
        )

        assert response.status_code == 201

        # Check that admin notification was queued
        messages = mock_transport.get_messages()
        assert len(messages) > 0

        # Find the notification (should be to admin_chat_id)
        admin_msg = next(
            (m for m in messages if "New Access Request" in m["message"]),
            None,
        )
        assert admin_msg is not None
        assert "Bob" in admin_msg["message"]
        assert "222222222" in admin_msg["message"]

    def test_create_request_response_schema(self, client: TestClient, test_db_session: Session):
        """Response contains required fields from Request schema."""
        response = client.post(
            "/requests",
            json={
                "telegram_id": 333333333,
                "first_name": "Charlie",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Check response schema matches OpenAPI contract
        assert "id" in data
        assert "telegram_id" in data
        assert "first_name" in data
        assert "status" in data
        assert "created_at" in data

        # Verify values
        assert data["telegram_id"] == 333333333
        assert data["first_name"] == "Charlie"
        assert data["status"] == "pending"

    def test_create_request_duplicate_rejected(self, client: TestClient, test_db_session: Session):
        """Duplicate request from same telegram_id is rejected with 400."""
        # Create first request
        response1 = client.post(
            "/requests",
            json={
                "telegram_id": 444444444,
                "first_name": "Dave",
            },
        )
        assert response1.status_code == 201

        # Try to create duplicate
        response2 = client.post(
            "/requests",
            json={
                "telegram_id": 444444444,
                "first_name": "Dave Different",
            },
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "error" in data or "detail" in data

    def test_create_request_with_minimal_fields(self, client: TestClient, test_db_session: Session):
        """Request creation works with only required fields (telegram_id, first_name)."""
        response = client.post(
            "/requests",
            json={
                "telegram_id": 555555555,
                "first_name": "Eve",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["telegram_id"] == 555555555
        assert data["first_name"] == "Eve"

    def test_create_request_with_all_fields(self, client: TestClient, test_db_session: Session):
        """Request creation accepts all optional fields."""
        response = client.post(
            "/requests",
            json={
                "telegram_id": 666666666,
                "first_name": "Frank",
                "last_name": "Brown",
                "telegram_username": "frank_b",
                "note": "Been using the app for 6 months",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Check database directly
        candidate = (
            test_db_session.query(TelegramUserCandidate).filter_by(telegram_id=666666666).first()
        )
        print(f"Database candidate username: {candidate.username}")
        print(f"Response data: {data}")

        assert data["last_name"] == "Brown"
        assert data["note"] == "Been using the app for 6 months"
        # Check the username was stored
        assert candidate.username == "frank_b"

    def test_multiple_requests_from_different_users(
        self, client: TestClient, test_db_session: Session
    ):
        """Multiple requests from different users are all created successfully."""
        user_ids = [777777777, 888888888, 999999999]

        for user_id in user_ids:
            response = client.post(
                "/requests",
                json={
                    "telegram_id": user_id,
                    "first_name": f"User{user_id}",
                },
            )
            assert response.status_code == 201

        # Verify all are in database
        candidates = test_db_session.query(TelegramUserCandidate).all()
        candidate_ids = [c.telegram_id for c in candidates]
        for user_id in user_ids:
            assert user_id in candidate_ids
