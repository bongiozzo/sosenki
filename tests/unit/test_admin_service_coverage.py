"""Unit tests for admin_service with expanded coverage."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from src.models.access_request import AccessRequest, RequestStatus
from src.models.user import User
from src.services.admin_service import AdminService


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def admin_user():
    """Create a mock admin user."""
    user = User(id=999, telegram_id=999, name="Admin", is_administrator=True, is_active=True)
    return user


@pytest.fixture
def admin_service(mock_db_session):
    """Create an AdminService instance with mock session."""
    return AdminService(mock_db_session)


class TestAdminServiceApprove:
    """Test cases for approving requests."""

    @pytest.mark.asyncio
    async def test_approve_request_success(self, admin_service, mock_db_session, admin_user):
        """Test successful request approval."""
        request = AccessRequest(
            id=1,
            user_telegram_id="123",
            user_telegram_username="testuser",
            request_message="Help",
            status=RequestStatus.PENDING,
        )
        mock_db_session.query.return_value.filter.return_value.first.return_value = request
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        result = await admin_service.approve_request(1, admin_user)

        assert result is not None
        assert result.status == RequestStatus.APPROVED
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_approve_request_with_user_selection(
        self, admin_service, mock_db_session, admin_user
    ):
        """Test approval with selected user linking."""
        request = AccessRequest(
            id=1,
            user_telegram_id="123",
            user_telegram_username="testuser",
            request_message="Help",
            status=RequestStatus.PENDING,
        )
        user = User(id=5, name="John", is_active=False)

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            request,
            user,
        ]
        mock_db_session.commit = MagicMock()

        result = await admin_service.approve_request(1, admin_user, selected_user_id=5)

        assert result is not None
        assert result.status == RequestStatus.APPROVED
        assert user.telegram_id == "123"
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_approve_request_not_found(self, admin_service, mock_db_session, admin_user):
        """Test approval fails for non-existent request."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        result = await admin_service.approve_request(999, admin_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_approve_request_selected_user_not_found(
        self, admin_service, mock_db_session, admin_user
    ):
        """Test approval fails when selected user not found."""
        request = AccessRequest(
            id=1,
            user_telegram_id="123",
            user_telegram_username="testuser",
            request_message="Help",
            status=RequestStatus.PENDING,
        )
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            request,
            None,
        ]

        result = await admin_service.approve_request(1, admin_user, selected_user_id=999)

        assert result is None

    @pytest.mark.asyncio
    async def test_approve_request_creates_user_if_not_exists(
        self, admin_service, mock_db_session, admin_user
    ):
        """Test approval creates user if not found by telegram_id."""
        request = AccessRequest(
            id=1,
            user_telegram_id="123",
            user_telegram_username="testuser",
            request_message="Help",
            status=RequestStatus.PENDING,
        )
        mock_db_session.query.return_value.filter.return_value.first.return_value = request
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        result = await admin_service.approve_request(1, admin_user)

        assert result is not None
        mock_db_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_request_exception_handling(
        self, admin_service, mock_db_session, admin_user
    ):
        """Test approval handles exceptions gracefully."""
        mock_db_session.query.return_value.filter.return_value.first.side_effect = Exception(
            "DB Error"
        )

        result = await admin_service.approve_request(1, admin_user)

        assert result is None
        mock_db_session.rollback.assert_called_once()


class TestAdminServiceReject:
    """Test cases for rejecting requests."""

    @pytest.mark.asyncio
    async def test_reject_request_success(self, admin_service, mock_db_session, admin_user):
        """Test successful request rejection."""
        request = AccessRequest(
            id=1,
            user_telegram_id="123",
            request_message="Help",
            status=RequestStatus.PENDING,
        )
        mock_db_session.query.return_value.filter.return_value.first.return_value = request
        mock_db_session.commit = MagicMock()

        result = await admin_service.reject_request(1, admin_user)

        assert result is not None
        assert result.status == RequestStatus.REJECTED
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_request_not_found(self, admin_service, mock_db_session, admin_user):
        """Test rejection fails for non-existent request."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        result = await admin_service.reject_request(999, admin_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_reject_request_exception_handling(
        self, admin_service, mock_db_session, admin_user
    ):
        """Test rejection handles exceptions gracefully."""
        mock_db_session.query.return_value.filter.return_value.first.side_effect = Exception(
            "DB Error"
        )

        result = await admin_service.reject_request(1, admin_user)

        assert result is None
        mock_db_session.rollback.assert_called_once()


class TestAdminServiceConfig:
    """Test cases for admin configuration."""

    @pytest.mark.asyncio
    async def test_get_admin_config(self, admin_service):
        """Test getting admin configuration."""
        result = await admin_service.get_admin_config()

        assert result is None
