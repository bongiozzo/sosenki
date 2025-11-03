"""Request submission service (US2)."""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.models.telegram_user_candidate import TelegramUserCandidate
from backend.app.logging import logger
from backend.app.services.telegram_bot import get_telegram_bot_service


class DuplicateRequestError(Exception):
    """Raised when a request with the same telegram_id already exists."""

    pass


def create_request(
    db: Session,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    note: str | None = None,
) -> TelegramUserCandidate:
    """
    Create a TelegramUserCandidate request record.

    Args:
        db: Database session
        telegram_id: Telegram user ID (must be unique)
        username: Telegram username
        first_name: User's first name
        last_name: User's last name
        phone: User's phone number
        email: User's email address
        note: Optional request note/comment

    Returns:
        The created TelegramUserCandidate instance

    Raises:
        DuplicateRequestError: If a request with this telegram_id already exists
    """
    # Check for existing request with same telegram_id
    existing = db.query(TelegramUserCandidate).filter_by(telegram_id=telegram_id).first()
    if existing:
        logger.warning(f"Duplicate request attempt for telegram_id: {telegram_id}")
        raise DuplicateRequestError(f"A request already exists for telegram_id {telegram_id}")

    candidate = TelegramUserCandidate(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        email=email,
        note=note,
        status="pending",
    )

    try:
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        logger.info(f"Created request for telegram_id: {telegram_id}")

        # Notify admin group about new request (fire-and-forget, only if event loop exists)
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            # Event loop exists, schedule the notification
            bot_service = get_telegram_bot_service()
            loop.create_task(
                bot_service.notify_admin_new_request(
                    telegram_id=telegram_id,
                    first_name=first_name or "Unknown",
                    last_name=last_name,
                    telegram_username=username,
                    note=note,
                )
            )
        except RuntimeError:
            # No event loop running (e.g., in unit tests) - skip notification
            logger.debug(
                f"No event loop for async notification, skipping for telegram_id: {telegram_id}"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin about new request: {e}")
            # Don't fail the request creation if notification fails

        return candidate
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError creating request for telegram_id {telegram_id}: {e}")
        raise DuplicateRequestError(
            f"A request already exists for telegram_id {telegram_id}"
        ) from e
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating request: {e}")
        raise
