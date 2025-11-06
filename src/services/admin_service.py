"""Admin service for approval and rejection workflows."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.access_request import AccessRequest, RequestStatus
from src.models.user import User

logger = logging.getLogger(__name__)


class AdminService:
    """Service for admin approval/rejection operations."""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def approve_request(
        self,
        request_id: int,
        admin_telegram_id: str,
    ) -> AccessRequest | None:
        """Approve a client request.

        T040, T042: Update status to approved, mark client as active.

        Args:
            request_id: Request ID to approve
            admin_telegram_id: Admin's Telegram ID

        Returns:
            Updated request object if successful, None otherwise
        """
        try:
            # Find the request
            request = self.db.query(AccessRequest).filter(
                AccessRequest.id == request_id
            ).first()

            if not request:
                logger.warning("Request %d not found for approval", request_id)
                return None

            # Update request status to approved
            request.status = RequestStatus.APPROVED
            request.responded_by_admin_id = admin_telegram_id
            request.response_message = "approved"
            request.responded_at = datetime.now(timezone.utc)

            # T042: Activate the user (set is_active=True)
            user = self.db.execute(
                select(User).where(User.telegram_id == request.user_telegram_id)
            ).scalar_one_or_none()
            
            if user:
                user.is_active = True
                logger.info("Activated user %s on approval", request.user_telegram_id)
            else:
                logger.warning("User %s not found for activation on approval", request.user_telegram_id)

            self.db.commit()
            logger.info("Request %d approved by admin %s", request_id, admin_telegram_id)
            return request

        except Exception as e:
            logger.error("Error approving request %d: %s", request_id, e, exc_info=True)
            self.db.rollback()
            return None

    async def reject_request(
        self,
        request_id: int,
        admin_telegram_id: str,
    ) -> AccessRequest | None:
        """Reject a client request.

        T040: Update status to rejected.

        Args:
            request_id: Request ID to reject
            admin_telegram_id: Admin's Telegram ID

        Returns:
            Updated request object if successful, None otherwise
        """
        try:
            # Find the request
            request = self.db.query(AccessRequest).filter(
                AccessRequest.id == request_id
            ).first()

            if not request:
                logger.warning("Request %d not found for rejection", request_id)
                return None

            # Update request status to rejected
            request.status = RequestStatus.REJECTED
            request.responded_by_admin_id = admin_telegram_id
            request.response_message = "rejected"
            request.responded_at = datetime.now(timezone.utc)

            self.db.commit()
            logger.info("Request %d rejected by admin %s", request_id, admin_telegram_id)
            return request

        except Exception as e:
            logger.error("Error rejecting request %d: %s", request_id, e, exc_info=True)
            self.db.rollback()
            return None

    async def get_admin_config(self) -> dict | None:
        """Get admin configuration.

        Returns:
            Admin config or None
        """
        # TODO: - Load admin from config or database
        pass


__all__ = ["AdminService"]
