"""Unit tests for NotificationService - Validates service layer exists and has required methods"""
from src.services.notification_service import NotificationService


class TestNotificationService:
    """Verify NotificationService is properly implemented with required methods"""

    def test_notification_service_has_send_message_method(self):
        """T059: NotificationService has send_message method"""
        assert hasattr(NotificationService, 'send_message')

    def test_notification_service_has_send_confirmation_to_client(self):
        """T059: NotificationService has send_confirmation_to_client method"""
        assert hasattr(NotificationService, 'send_confirmation_to_client')

    def test_notification_service_has_send_notification_to_admin(self):
        """T059: NotificationService has send_notification_to_admin method"""
        assert hasattr(NotificationService, 'send_notification_to_admin')

    def test_notification_service_has_send_welcome_message(self):
        """T059: NotificationService has send_welcome_message method"""
        assert hasattr(NotificationService, 'send_welcome_message')

    def test_notification_service_has_send_rejection_message(self):
        """T059: NotificationService has send_rejection_message method"""
        assert hasattr(NotificationService, 'send_rejection_message')
