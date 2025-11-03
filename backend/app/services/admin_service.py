"""Admin request handling service (US3)."""

import asyncio
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.models.telegram_user_candidate import TelegramUserCandidate
from backend.app.models.admin_action import AdminAction
from backend.app.models.user import SOSenkiUser
from backend.app.logging import logger
from backend.app.services.telegram_bot import get_telegram_bot_service


class UserAlreadyExistsError(Exception):
    """Raised when attempting to create a user with a telegram_id that already exists."""

    pass


def accept_request(
    db: Session,
    request_id: int,
    admin_id: int,
) -> SOSenkiUser:
    """
    Accept a pending request and create a SOSenkiUser.

    Args:
        db: Database session
        request_id: ID of the TelegramUserCandidate request to accept
        admin_id: ID of the admin performing the action

    Returns:
        The created SOSenkiUser instance

    Raises:
        UserAlreadyExistsError: If a user with this telegram_id already exists
    """
    # Fetch the candidate request
    candidate = db.query(TelegramUserCandidate).filter_by(id=request_id).first()
    if not candidate:
        logger.error(f"Request {request_id} not found")
        raise ValueError(f"Request {request_id} not found")

    # Check if user already exists with this telegram_id
    existing_user = db.query(SOSenkiUser).filter_by(telegram_id=candidate.telegram_id).first()
    if existing_user:
        logger.warning(
            f"User already exists for telegram_id {candidate.telegram_id} (request {request_id})"
        )
        raise UserAlreadyExistsError(f"User already exists for telegram_id {candidate.telegram_id}")

    try:
        # Create the SOSenkiUser
        user = SOSenkiUser(
            telegram_id=candidate.telegram_id,
            username=candidate.username,
            email=candidate.email,
            roles=["user"],  # Default role on acceptance
        )
        db.add(user)
        db.flush()  # Get the id before committing

        # Create audit record
        audit = AdminAction(
            admin_id=admin_id,
            request_id=request_id,
            action="accept",
        )
        db.add(audit)

        # Update candidate status
        candidate.status = "accepted"

        db.commit()
        db.refresh(user)

        logger.info(f"Request {request_id} accepted by admin {admin_id}, user {user.id} created")

        # Notify user of acceptance (fire-and-forget)
        try:
            loop = asyncio.get_running_loop()
            bot_service = get_telegram_bot_service()
            loop.create_task(
                bot_service.notify_user_request_accepted(
                    telegram_id=candidate.telegram_id,
                    role="user",
                )
            )
        except RuntimeError:
            # No event loop running (e.g., in unit tests) - skip notification
            logger.debug(
                "No event loop for async notification, skipping for telegram_id: "
                f"{candidate.telegram_id}"
            )
        except Exception as e:
            logger.error(f"Failed to notify user of request acceptance: {e}")
            # Don't fail the request acceptance if notification fails

        return user

    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError accepting request {request_id}: {e}")
        if "telegram_id" in str(e):
            raise UserAlreadyExistsError(
                f"User already exists for telegram_id {candidate.telegram_id}"
            ) from e
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error accepting request {request_id}: {e}")
        raise


def reject_request(
    db: Session,
    request_id: int,
    admin_id: int,
    reason: str | None = None,
) -> None:
    """
    Reject a pending request.

    Args:
        db: Database session
        request_id: ID of the TelegramUserCandidate request to reject
        admin_id: ID of the admin performing the action
        reason: Optional reason for rejection
    """
    # Fetch the candidate request
    candidate = db.query(TelegramUserCandidate).filter_by(id=request_id).first()
    if not candidate:
        logger.error(f"Request {request_id} not found")
        raise ValueError(f"Request {request_id} not found")

    try:
        # Create audit record
        audit = AdminAction(
            admin_id=admin_id,
            request_id=request_id,
            action="reject",
            reason=reason,
        )
        db.add(audit)

        # Update candidate status
        candidate.status = "rejected"

        db.commit()

        logger.info(f"Request {request_id} rejected by admin {admin_id}")

        # Notify user of rejection (fire-and-forget)
        try:
            loop = asyncio.get_running_loop()
            bot_service = get_telegram_bot_service()
            loop.create_task(
                bot_service.notify_user_request_rejected(
                    telegram_id=candidate.telegram_id,
                    comment=reason,
                )
            )
        except RuntimeError:
            # No event loop running (e.g., in unit tests) - skip notification
            logger.debug(
                "No event loop for async notification, skipping for telegram_id: "
                f"{candidate.telegram_id}"
            )
        except Exception as e:
            logger.error(f"Failed to notify user of request rejection: {e}")
            # Don't fail the request rejection if notification fails

    except Exception as e:
        db.rollback()
        logger.error(f"Error rejecting request {request_id}: {e}")
        raise


def get_pending_requests(db: Session) -> list[TelegramUserCandidate]:
    """
    Get all pending requests.

    Args:
        db: Database session

    Returns:
        List of pending TelegramUserCandidate records
    """
    return (
        db.query(TelegramUserCandidate)
        .filter_by(status="pending")
        .order_by(TelegramUserCandidate.created_at)
        .all()
    )
