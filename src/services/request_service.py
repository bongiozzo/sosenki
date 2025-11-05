"""Request service for managing client access requests."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import ClientRequest, RequestStatus


class RequestService:
    """Service for managing client requests."""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def create_request(
        self, client_telegram_id: str, request_message: str
    ) -> ClientRequest | None:
        """Create a new request from a client.

        Validates that no pending request exists for this client,
        then creates a new ClientRequest with status=pending.

        Args:
            client_telegram_id: Client's Telegram ID
            request_message: Request message text

        Returns:
            Created ClientRequest or None if validation fails (duplicate pending request)
        """
        # T028: Check for existing PENDING request from this client
        existing_pending = self.db.execute(
            select(ClientRequest).where(
                ClientRequest.client_telegram_id == client_telegram_id,
                ClientRequest.status == RequestStatus.PENDING,
            )
        ).scalar_one_or_none()

        if existing_pending:
            # Client already has a pending request
            return None

        # Create new request
        new_request = ClientRequest(
            client_telegram_id=client_telegram_id,
            request_message=request_message,
            status=RequestStatus.PENDING,
            submitted_at=datetime.now(timezone.utc),
        )

        self.db.add(new_request)
        self.db.commit()
        self.db.refresh(new_request)

        return new_request

    async def get_pending_request(self, client_telegram_id: str) -> ClientRequest | None:
        """Get pending request for a client.

        Args:
            client_telegram_id: Client's Telegram ID

        Returns:
            Pending ClientRequest or None if not found
        """
        # T039: Query database for status=pending request from this client
        return self.db.execute(
            select(ClientRequest).where(
                ClientRequest.client_telegram_id == client_telegram_id,
                ClientRequest.status == RequestStatus.PENDING,
            )
        ).scalar_one_or_none()

    async def get_request_by_id(self, request_id: int) -> ClientRequest | None:
        """Get request by ID.

        Args:
            request_id: Request ID

        Returns:
            ClientRequest or None if not found
        """
        return self.db.execute(
            select(ClientRequest).where(ClientRequest.id == request_id)
        ).scalar_one_or_none()

    async def update_request_status(
        self,
        request_id: int,
        new_status: RequestStatus,
        admin_telegram_id: str,
        admin_response: str,
    ) -> bool:
        """Update request status after admin action.

        Args:
            request_id: Request ID
            new_status: New status (approved/rejected)
            admin_telegram_id: Admin's Telegram ID
            admin_response: Admin's response message

        Returns:
            True if successful, False otherwise
        """
        # T040: Query, update status and admin details, commit
        request = self.db.execute(
            select(ClientRequest).where(ClientRequest.id == request_id)
        ).scalar_one_or_none()

        if not request:
            return False

        request.status = new_status
        request.admin_telegram_id = admin_telegram_id
        request.admin_response = admin_response
        request.responded_at = datetime.now(timezone.utc)

        self.db.commit()
        return True


__all__ = ["RequestService"]
