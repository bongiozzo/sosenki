"""Request service for managing client access requests."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import AccessRequest, RequestStatus, User

logger = logging.getLogger(__name__)


class RequestService:
    """Service for managing client requests."""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def create_request(
        self, user_telegram_id: str, request_message: str
    ) -> AccessRequest | None:
        """Create a new request from a client.

        Validates that no pending request exists for this client,
        then creates a new AccessRequest with status=pending.
        Also ensures the user exists in the users table (foreign key requirement).

        Args:
            user_telegram_id: Client's Telegram ID
            request_message: Request message text

        Returns:
            Created AccessRequest or None if validation fails (duplicate pending request)
        """
        # T028: Check for existing PENDING request from this client
        existing_pending = self.db.execute(
            select(AccessRequest).where(
                AccessRequest.user_telegram_id == user_telegram_id,
                AccessRequest.status == RequestStatus.PENDING,
            )
        ).scalar_one_or_none()

        if existing_pending:
            # Client already has a pending request
            return None

        # Ensure user exists in users table (required for foreign key)
        existing_user = self.db.execute(
            select(User).where(User.telegram_id == user_telegram_id)
        ).scalar_one_or_none()

        if not existing_user:
            # Create user with is_active=False (will be activated on approval)
            # Generate a placeholder name from telegram_id since name is required and unique
            placeholder_name = f"User_{user_telegram_id}"
            user = User(
                telegram_id=user_telegram_id,
                name=placeholder_name,
                is_active=False,  # Not active until approved
            )
            self.db.add(user)
            self.db.flush()  # Ensure user is written before creating request
            logger.info("Created new user %s for request", user_telegram_id)

        # Create new request
        new_request = AccessRequest(
            user_telegram_id=user_telegram_id,
            request_message=request_message,
            status=RequestStatus.PENDING,
            submitted_at=datetime.now(timezone.utc),
        )

        self.db.add(new_request)
        self.db.commit()
        self.db.refresh(new_request)

        return new_request

    async def get_pending_request(self, user_telegram_id: str) -> AccessRequest | None:
        """Get pending request for a client.

        Args:
            user_telegram_id: Client's Telegram ID

        Returns:
            Pending AccessRequest or None if not found
        """
        # T039: Query database for status=pending request from this client
        return self.db.execute(
            select(AccessRequest).where(
                AccessRequest.user_telegram_id == user_telegram_id,
                AccessRequest.status == RequestStatus.PENDING,
            )
        ).scalar_one_or_none()

    async def get_request_by_id(self, request_id: int) -> AccessRequest | None:
        """Get request by ID.

        Args:
            request_id: Request ID

        Returns:
            AccessRequest or None if not found
        """
        return self.db.execute(
            select(AccessRequest).where(AccessRequest.id == request_id)
        ).scalar_one_or_none()

    async def update_request_status(
        self,
        request_id: int,
        new_status: RequestStatus,
        responded_by_admin_id: str,
        response_message: str,
    ) -> bool:
        """Update request status after admin action.

        Args:
            request_id: Request ID
            new_status: New status (approved/rejected)
            responded_by_admin_id: Admin's Telegram ID
            response_message: Admin's response message

        Returns:
            True if successful, False otherwise
        """
        # T040: Query, update status and admin details, commit
        request = self.db.execute(
            select(AccessRequest).where(AccessRequest.id == request_id)
        ).scalar_one_or_none()

        if not request:
            return False

        request.status = new_status
        request.responded_by_admin_id = responded_by_admin_id
        request.response_message = response_message
        request.responded_at = datetime.now(timezone.utc)

        self.db.commit()
        return True


__all__ = ["RequestService"]
