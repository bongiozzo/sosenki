"""Unit tests for request_service with expanded coverage."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from src.models import AccessRequest, RequestStatus
from src.services.request_service import RequestService


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def request_service(mock_db_session):
    """Create a RequestService instance with mock session."""
    return RequestService(mock_db_session)


class TestRequestServiceCreate:
    """Test cases for creating requests."""

    @pytest.mark.asyncio
    async def test_create_request_success(self, request_service, mock_db_session):
        """Test successful request creation."""
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_db_session.add = MagicMock()
        mock_db_session.commit = MagicMock()
        mock_db_session.refresh = MagicMock()

        result = await request_service.create_request("123", "Help needed", "testuser")

        assert result is not None
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_request_duplicate_pending(self, request_service, mock_db_session):
        """Test request creation fails with existing pending request."""
        existing_request = AccessRequest(
            user_telegram_id="123",
            request_message="Existing",
            status=RequestStatus.PENDING,
        )
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = existing_request

        result = await request_service.create_request("123", "New request")

        assert result is None
        mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_request_no_username(self, request_service, mock_db_session):
        """Test request creation without username."""
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        result = await request_service.create_request("123", "Help needed")

        assert result is not None
        mock_db_session.add.assert_called_once()


class TestRequestServiceGet:
    """Test cases for retrieving requests."""

    @pytest.mark.asyncio
    async def test_get_pending_request_found(self, request_service, mock_db_session):
        """Test getting pending request that exists."""
        pending_request = AccessRequest(
            id=1,
            user_telegram_id="123",
            request_message="Help",
            status=RequestStatus.PENDING,
        )
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = pending_request

        result = await request_service.get_pending_request("123")

        assert result is not None
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_get_pending_request_not_found(self, request_service, mock_db_session):
        """Test getting pending request that doesn't exist."""
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        result = await request_service.get_pending_request("123")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_request_by_id_found(self, request_service, mock_db_session):
        """Test getting request by ID that exists."""
        existing_request = AccessRequest(
            id=1,
            user_telegram_id="123",
            request_message="Help",
            status=RequestStatus.PENDING,
        )
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = existing_request

        result = await request_service.get_request_by_id(1)

        assert result is not None
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_get_request_by_id_not_found(self, request_service, mock_db_session):
        """Test getting request by ID that doesn't exist."""
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        result = await request_service.get_request_by_id(999)

        assert result is None


class TestRequestServiceUpdate:
    """Test cases for updating request status."""

    @pytest.mark.asyncio
    async def test_update_request_status_success(self, request_service, mock_db_session):
        """Test successful status update."""
        existing_request = AccessRequest(
            id=1,
            user_telegram_id="123",
            request_message="Help",
            status=RequestStatus.PENDING,
        )
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = existing_request

        result = await request_service.update_request_status(
            1, RequestStatus.APPROVED, "admin123", "Approved"
        )

        assert result is True
        assert existing_request.status == RequestStatus.APPROVED
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_request_status_not_found(self, request_service, mock_db_session):
        """Test status update fails for non-existent request."""
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        result = await request_service.update_request_status(
            999, RequestStatus.APPROVED, "admin123", "Approved"
        )

        assert result is False
        mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_request_status_no_response(self, request_service, mock_db_session):
        """Test status update without admin response."""
        existing_request = AccessRequest(
            id=1,
            user_telegram_id="123",
            request_message="Help",
            status=RequestStatus.PENDING,
        )
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = existing_request

        result = await request_service.update_request_status(1, RequestStatus.REJECTED, "admin123")

        assert result is True
        assert existing_request.status == RequestStatus.REJECTED
