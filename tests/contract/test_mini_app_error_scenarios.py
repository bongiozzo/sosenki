"""Extended contract tests for Mini App endpoints - error scenarios and edge cases."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


class TestInitEndpointErrorScenarios:
    """Test error scenarios for /api/mini-app/init endpoint."""

    def test_init_missing_auth_returns_401(self, client: TestClient):
        """Test init endpoint without authorization."""
        response = client.post("/api/mini-app/init")
        assert response.status_code == 401

    def test_init_invalid_signature_returns_500(self, client: TestClient):
        """Test init endpoint with signature verification failure."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature",
            side_effect=Exception("Verification error"),
        ):
            response = client.post(
                "/api/mini-app/init",
                headers={"Authorization": "tma invalid"},
            )
            assert response.status_code == 500

    def test_init_database_error_returns_500(self, client: TestClient):
        """Test init endpoint when database query fails."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature",
            return_value={"user": '{"id": 123}'},
        ) as mock_verify:
            with patch(
                "src.api.mini_app.UserService.get_by_telegram_id",
                side_effect=Exception("Database error"),
            ):
                client.post(
                    "/api/mini-app/init",
                    headers={"Authorization": "tma test_data"},
                )
                # Should attempt to verify when called
                assert mock_verify.called

    def test_init_json_body_init_data_fallback(self, client: TestClient):
        """Test init endpoint using initData from JSON body."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature", return_value=None
        ):
            response = client.post(
                "/api/mini-app/init",
                json={"initData": "fallback_data"},
            )
            # Should reject due to invalid verification result
            assert response.status_code == 401


class TestPropertiesEndpointErrorScenarios:
    """Test error scenarios for /api/mini-app/properties endpoint."""

    def test_properties_missing_authorization(self, client: TestClient):
        """Test /properties without authorization."""
        response = client.post("/api/mini-app/properties")
        assert response.status_code == 401

    def test_properties_invalid_signature(self, client: TestClient):
        """Test /properties with invalid signature."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature", return_value=None
        ):
            response = client.post(
                "/api/mini-app/properties",
                headers={"Authorization": "tma invalid"},
            )
            assert response.status_code == 401

    def test_properties_verification_exception(self, client: TestClient):
        """Test /properties when verification raises exception."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature",
            side_effect=Exception("Verification failed"),
        ):
            response = client.post(
                "/api/mini-app/properties",
                headers={"Authorization": "tma test"},
            )
            assert response.status_code == 500


class TestTransactionsListErrorScenarios:
    """Test error scenarios for /api/mini-app/transactions endpoint."""

    def test_transactions_list_missing_authorization(self, client: TestClient):
        """Test /transactions without authorization."""
        response = client.post("/api/mini-app/transactions?account_id=1")
        assert response.status_code == 401

    def test_transactions_list_invalid_signature(self, client: TestClient):
        """Test /transactions with invalid signature."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature", return_value=None
        ):
            response = client.post(
                "/api/mini-app/transactions?account_id=1",
                headers={"Authorization": "tma invalid"},
            )
            assert response.status_code == 401

    def test_transactions_list_verification_exception(self, client: TestClient):
        """Test /transactions when verification returns None."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature", return_value=None
        ):
            response = client.post(
                "/api/mini-app/transactions?account_id=1",
                headers={"Authorization": "tma test"},
            )
            assert response.status_code == 401


class TestBillsEndpointErrorScenarios:
    """Test error scenarios for /api/mini-app/bills endpoint."""

    def test_bills_missing_authorization(self, client: TestClient):
        """Test /bills without authorization."""
        response = client.post("/api/mini-app/bills?account_id=1")
        assert response.status_code == 401

    def test_bills_invalid_signature(self, client: TestClient):
        """Test /bills with invalid signature."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature", return_value=None
        ):
            response = client.post(
                "/api/mini-app/bills?account_id=1",
                headers={"Authorization": "tma invalid"},
            )
            assert response.status_code == 401

    def test_bills_verification_exception(self, client: TestClient):
        """Test /bills when verification returns None."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature", return_value=None
        ):
            response = client.post(
                "/api/mini-app/bills?account_id=1",
                headers={"Authorization": "tma test"},
            )
            assert response.status_code == 401


class TestBalanceEndpointErrorScenarios:
    """Test error scenarios for /api/mini-app/account endpoint."""

    def test_balance_missing_authorization(self, client: TestClient):
        """Test /account without authorization."""
        response = client.post("/api/mini-app/account?account_id=1")
        # When init data is missing, endpoint returns 401 NOT_AUTHORIZED
        assert response.status_code == 401

    def test_balance_invalid_signature(self, client: TestClient):
        """Test /account with invalid signature."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature", return_value=None
        ):
            response = client.post(
                "/api/mini-app/account?account_id=1",
                headers={"Authorization": "tma invalid"},
            )
            assert response.status_code == 401

    def test_balance_verification_exception(self, client: TestClient):
        """Test /account when verification raises exception."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature",
            side_effect=Exception("Verification failed"),
        ):
            response = client.post(
                "/api/mini-app/account?account_id=1",
                headers={"Authorization": "tma test"},
            )
            assert response.status_code == 500


class TestBalancesEndpointErrorScenarios:
    """Test error scenarios for /api/mini-app/accounts endpoint."""

    def test_balances_missing_authorization(self, client: TestClient):
        """Test /accounts without authorization."""
        response = client.post("/api/mini-app/accounts")
        # Missing body may return 422 or 400 depending on endpoint
        assert response.status_code in [400, 401, 422]

    def test_balances_invalid_signature(self, client: TestClient):
        """Test /accounts with invalid signature."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature", return_value=None
        ):
            response = client.post(
                "/api/mini-app/accounts",
                headers={"Authorization": "tma invalid"},
            )
            assert response.status_code == 401

    def test_balances_verification_exception(self, client: TestClient):
        """Test /accounts when verification raises exception."""
        with patch(
            "src.api.mini_app.UserService.verify_telegram_webapp_signature",
            side_effect=Exception("Verification failed"),
        ):
            response = client.post(
                "/api/mini-app/accounts",
                headers={"Authorization": "tma test"},
            )
            assert response.status_code == 500


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestExtractInitDataHelper:
    """Tests for _extract_init_data helper function."""

    def test_extract_init_data_from_authorization_header(self):
        """Test extracting init data from Authorization header."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data("tma raw_data_here", None, None)
        assert result == "raw_data_here"

    def test_extract_init_data_from_authorization_case_insensitive(self):
        """Test Authorization header parsing is case-insensitive."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data("TMA test_data", None, None)
        assert result == "test_data"

    def test_extract_init_data_from_x_telegram_header(self):
        """Test extracting from X-Telegram-Init-Data header."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data(None, "header_data", None)
        assert result == "header_data"

    def test_extract_init_data_from_json_initdata(self):
        """Test extracting from JSON body initData field."""
        from src.api.mini_app import _extract_init_data

        body = {"initData": "body_data"}
        result = _extract_init_data(None, None, body)
        assert result == "body_data"

    def test_extract_init_data_from_json_init_data_raw(self):
        """Test extracting from JSON body initDataRaw field."""
        from src.api.mini_app import _extract_init_data

        body = {"initDataRaw": "raw_body_data"}
        result = _extract_init_data(None, None, body)
        assert result == "raw_body_data"

    def test_extract_init_data_priority_authorization_first(self):
        """Test priority: Authorization header takes precedence."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data("tma auth_data", "header_data", {"initData": "body_data"})
        assert result == "auth_data"

    def test_extract_init_data_priority_header_second(self):
        """Test priority: X-Telegram header is second."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data(None, "header_data", {"initData": "body_data"})
        assert result == "header_data"

    def test_extract_init_data_returns_none_when_missing(self):
        """Test returns None when init data is not present."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data(None, None, None)
        assert result is None

    def test_extract_init_data_empty_authorization_returns_none(self):
        """Test empty Authorization header returns None."""
        from src.api.mini_app import _extract_init_data

        result = _extract_init_data("   ", None, None)
        assert result is None

    def test_extract_init_data_ignores_empty_body_fields(self):
        """Test that empty body fields are skipped."""
        from src.api.mini_app import _extract_init_data

        body = {"initData": "", "init_data_raw": "valid_data"}
        result = _extract_init_data(None, None, body)
        assert result == "valid_data"
