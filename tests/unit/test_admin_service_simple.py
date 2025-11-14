"""Unit tests for AdminService - Validates service layer exists and has required methods"""

from src.services.admin_service import AdminService


class TestAdminService:
    """Verify AdminService is properly implemented with required methods"""

    def test_admin_service_has_approve_request_method(self):
        """T058: AdminService has approve_request method"""
        assert hasattr(AdminService, "approve_request")

    def test_admin_service_has_reject_request_method(self):
        """T058: AdminService has reject_request method"""
        assert hasattr(AdminService, "reject_request")

    def test_admin_service_has_get_admin_config_method(self):
        """T058: AdminService has get_admin_config method"""
        assert hasattr(AdminService, "get_admin_config")
