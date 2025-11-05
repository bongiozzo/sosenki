"""Admin service for approval and rejection workflows."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.models.access_request import AccessRequest, RequestStatus


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
                return None

            # Update request status to approved
            request.status = RequestStatus.APPROVED
            request.admin_telegram_id = admin_telegram_id
            request.admin_response = "approved"
            request.responded_at = datetime.now(timezone.utc)

            self.db.commit()
            return request

        except Exception:
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
                return None

            # Update request status to rejected
            request.status = RequestStatus.REJECTED
            request.admin_telegram_id = admin_telegram_id
            request.admin_response = "rejected"
            request.responded_at = datetime.now(timezone.utc)

            self.db.commit()
            return request

        except Exception:
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
