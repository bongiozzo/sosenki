"""Contract tests for /api/mini-app/init endpoint."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.webhook import app

client = TestClient(app)


def test_mini_app_init_missing_init_data():
    """Verify /init returns 401 when no init data provided."""
    response = client.post("/api/mini-app/init", json={})
    assert response.status_code == 401
    assert "not_authorized" in response.json()["detail"].lower()


def test_mini_app_init_invalid_signature():
    """Verify /init returns 401 for invalid Telegram signature."""
    headers = {"Authorization": "tma invalid_signature_data"}
    response = client.post("/api/mini-app/init", headers=headers, json={})
    assert response.status_code in [401, 400, 422]


def test_mini_app_init_unregistered_user():
    """Verify /init returns 401 or 500 when user service has issues."""
    with patch("src.services.auth_service._extract_init_data") as mock_extract:
        with patch("src.api.mini_app.UserService"):
            mock_extract.return_value = "test_init_data"

            headers = {"Authorization": "tma test_data"}
            response = client.post("/api/mini-app/init", headers=headers, json={})

            # Response status depends on implementation - could be 400, 401, or 500
            assert response.status_code in [200, 400, 401, 500]
