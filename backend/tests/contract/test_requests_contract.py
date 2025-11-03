"""Contract tests for POST /requests endpoint (US2 — Request submission)."""

import pytest
from fastapi.testclient import TestClient
from backend.app.models.telegram_user_candidate import TelegramUserCandidate
from backend.app.database import SessionLocal


class TestRequestsContract:
    """Contract tests for request submission endpoint."""

    def test_requests_endpoint_exists(self, client: TestClient):
        """POST /requests endpoint exists and returns 201."""
        payload = {
            "telegram_id": 123456789,
            "telegram_username": "test_user",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1234567890",
            "email": "john@example.com",
        }
        response = client.post("/requests", json=payload)
        assert response.status_code == 201

    def test_requests_creates_telegram_user_candidate(self, client: TestClient, test_db_session):
        """POST /requests creates a TelegramUserCandidate record in the database."""
        payload = {
            "telegram_id": 987654321,
            "telegram_username": "alice_user",
            "first_name": "Alice",
            "last_name": "Smith",
            "phone": "+9876543210",
            "email": "alice@example.com",
        }
        response = client.post("/requests", json=payload)
        assert response.status_code == 201

        # Verify the record was created in the database
        candidate = (
            test_db_session.query(TelegramUserCandidate).filter_by(telegram_id=987654321).first()
        )
        assert candidate is not None
        assert candidate.username == "alice_user"
        assert candidate.first_name == "Alice"
        assert candidate.status == "pending"

    def test_requests_response_schema(self, client: TestClient):
        """POST /requests response matches expected schema."""
        payload = {
            "telegram_id": 111111111,
            "telegram_username": "bob_user",
            "first_name": "Bob",
            "last_name": "Johnson",
            "phone": "+1111111111",
            "email": "bob@example.com",
        }
        response = client.post("/requests", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert data["telegram_id"] == 111111111
        assert data["telegram_username"] == "bob_user"
        assert data["status"] == "pending"
        assert "created_at" in data

    def test_requests_duplicate_telegram_id_returns_400(self, client: TestClient):
        """POST /requests with duplicate telegram_id returns 400 Conflict."""
        payload = {
            "telegram_id": 555555555,
            "telegram_username": "charlie",
            "first_name": "Charlie",
            "last_name": "Brown",
            "phone": "+5555555555",
            "email": "charlie@example.com",
        }

        # First request succeeds
        response1 = client.post("/requests", json=payload)
        assert response1.status_code == 201

        # Second request with same telegram_id fails
        response2 = client.post("/requests", json=payload)
        assert response2.status_code == 400
        error_data = response2.json()
        assert "detail" in error_data or "error_code" in error_data

    def test_requests_missing_required_fields_returns_422(self, client: TestClient):
        """POST /requests with missing required fields returns 422."""
        payload = {"telegram_username": "incomplete"}
        response = client.post("/requests", json=payload)
        assert response.status_code == 422
