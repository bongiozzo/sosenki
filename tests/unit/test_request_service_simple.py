"""Unit tests for RequestService - Validates service layer exists and has required methods"""

from src.services.request_service import RequestService


class TestRequestService:
    """Verify RequestService is properly implemented with required methods"""

    def test_request_service_has_create_request_method(self):
        """T060: RequestService has create_request method"""
        assert hasattr(RequestService, "create_request")

    def test_request_service_has_get_pending_request_method(self):
        """T060: RequestService has get_pending_request method"""
        assert hasattr(RequestService, "get_pending_request")

    def test_request_service_has_get_request_by_id_method(self):
        """T060: RequestService has get_request_by_id method"""
        assert hasattr(RequestService, "get_request_by_id")

    def test_request_service_has_update_request_status_method(self):
        """T060: RequestService has update_request_status method"""
        assert hasattr(RequestService, "update_request_status")
