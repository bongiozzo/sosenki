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
        selected_user_id: int | None = None,
    ) -> AccessRequest | None:
        """Approve a client request.

        T040, T042: Update status to approved, mark client as active.

        When selected_user_id is provided, links the request creator (via client_telegram_id)
        to the selected user and assigns their Telegram ID and username.

        Args:
            request_id: Request ID to approve
            admin_telegram_id: Admin's Telegram ID
            selected_user_id: If provided, assign Telegram ID to user with this ID

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

            # Get the requester's username from the stored request
            requester_username = request.user_telegram_username

            # If user ID provided, link request creator to that user
            if selected_user_id is not None and selected_user_id > 0:
                selected_user = self.db.query(User).filter(
                    User.id == selected_user_id
                ).first()

                if selected_user:
                    # Assign the request creator's Telegram credentials to the selected user
                    selected_user.telegram_id = request.user_telegram_id
                    selected_user.username = requester_username
                    logger.info(
                        "Assigned Telegram ID %s (username: %s) to user %s (ID: %d)",
                        request.user_telegram_id,
                        requester_username,
                        selected_user.name,
                        selected_user.id
                    )
                else:
                    logger.warning("User ID %d not found for Telegram assignment", selected_user_id)
                    return None

            # Update request status to approved
            request.status = RequestStatus.APPROVED
            request.responded_by_admin_id = admin_telegram_id
            request.response_message = "approved"
            request.responded_at = datetime.now(timezone.utc)

            # T042: Activate the user (set is_active=True)
            # If selected_user_id was provided, we already updated that user above
            if selected_user_id is not None and selected_user_id > 0:
                # User was already updated above, just mark it as active
                selected_user.is_active = True
                logger.info("Activated selected user ID %d on approval", selected_user_id)
            else:
                # No selected user, find or create user by telegram_id
                user = self.db.execute(
                    select(User).where(User.telegram_id == request.user_telegram_id)
                ).scalar_one_or_none()

                if user:
                    user.is_active = True
                    logger.info("Activated user %s on approval", request.user_telegram_id)
                else:
                    # Create user if it doesn't exist (user should be created on first approval)
                    placeholder_name = f"User_{request.user_telegram_id}"
                    user = User(
                        telegram_id=request.user_telegram_id,
                        name=placeholder_name,
                        is_active=True
                    )
                    self.db.add(user)
                    logger.info("Created new user %s on approval", request.user_telegram_id)

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
