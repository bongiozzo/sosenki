"""Admin bot handlers for request approval and rejection."""

import logging
import re
from typing import Literal

from telegram import Update
from telegram.ext import ContextTypes

from src.models.access_request import AccessRequest
from src.models.user import User
from src.services import AsyncSessionLocal
from src.services.admin_service import AdminService
from src.services.auth_service import verify_bot_admin_authorization
from src.services.localizer import t
from src.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


async def _execute_admin_action(
    action: Literal["approve", "reject"],
    request_id: int,
    admin_user: User,
    context: ContextTypes.DEFAULT_TYPE,
    selected_user_id: int | None = None,
) -> tuple[AccessRequest | None, str | None]:
    """Execute approve or reject action on an access request.

    This is the shared business logic for both text reply and callback handlers.

    Args:
        action: Either "approve" or "reject"
        request_id: The access request ID to process
        admin_user: The authenticated admin user
        context: Telegram context for sending notifications
        selected_user_id: Optional user ID for approval (when matching to existing user)

    Returns:
        Tuple of (processed_request, error_message).
        If successful, error_message is None.
        If failed, request is None and error_message contains the localized error.
    """
    async with AsyncSessionLocal() as session:
        admin_service = AdminService(session)

        if action == "approve":
            request = await admin_service.approve_request(
                request_id=request_id,
                admin_user=admin_user,
                selected_user_id=selected_user_id,
            )
            if not request:
                return None, t("err_request_not_found_or_invalid")

            # Send welcome notification to the approved user
            notification_service = NotificationService(context.application)
            await notification_service.send_welcome_message(requester_id=request.user_telegram_id)
            return request, None

        else:  # reject
            request = await admin_service.reject_request(
                request_id=request_id, admin_user=admin_user
            )
            if not request:
                return None, t("err_request_not_found")

            # Send rejection notification to the user
            notification_service = NotificationService(context.application)
            await notification_service.send_rejection_message(requester_id=request.user_telegram_id)
            return request, None


async def handle_admin_response(  # noqa: C901
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Universal admin response handler.

    This handles both Approve and Reject replies to request notifications.
    The handler validates the reply, extracts the request id from the
    replied-to notification text, and then performs approve or reject
    actions atomically.

    IMPORTANT: This handler ONLY processes replies to request notifications
    (messages containing '#<id>' pattern). Other replies are silently ignored
    to allow them to be processed by other handlers (e.g., /ask LLM handler).
    """
    try:
        if not update.message or not update.message.from_user:
            logger.warning("Received admin response without message or user info")
            return

        # Must be a reply to the original notification
        if not update.message.reply_to_message:
            # Not a reply - silently ignore, let other handlers process
            return

        # CRITICAL: Only handle replies to request notifications
        # Request notifications contain '#<id>' pattern (e.g., "Request #123:")
        reply_text = update.message.reply_to_message.text or ""
        if not re.search(r"#\d+", reply_text):
            # Not a request notification - silently ignore
            # This allows the message to be processed by other handlers (e.g., /ask)
            return

        admin_id = str(update.message.from_user.id)
        admin_name = update.message.from_user.username or "Admin"

        text = (update.message.text or "").strip()

        # Check if input is a number (user ID selection)
        selected_user_id = None
        try:
            if text.isdigit():
                selected_user_id = int(text)
                action = "approve"  # Numeric selection always means approve
                logger.info("User ID selection detected: %d", selected_user_id)
            else:
                # Reply to request notification but not a valid action
                # Show helpful error since user clearly intended to interact with request
                logger.debug("Non-action reply to request from %s: %s", admin_id, text)
                try:
                    await update.message.reply_text(t("msg_reply_with_id_or_action"))
                except Exception:
                    logger.debug(
                        "Could not send instruction reply to admin %s", admin_id, exc_info=True
                    )
                return
        except ValueError:
            logger.warning("Could not parse admin response from %s: %s", admin_id, text)
            try:
                await update.message.reply_text(t("msg_invalid_response"))
            except Exception:
                logger.debug(
                    "Could not send parse error reply to admin %s", admin_id, exc_info=True
                )
            return

        # Parse request id from the replied-to message
        # We already validated that reply_text contains #<id> pattern above
        try:
            match = re.search(r"#(\d+)", reply_text)
            if match:
                request_id = int(match.group(1))
            else:
                # Should not happen since we checked the pattern above
                raise ValueError("Message format not recognized - could not find '#<id>'")
        except (ValueError, IndexError) as e:
            logger.warning("Could not parse request ID from message: %s (error: %s)", reply_text, e)
            try:
                await update.message.reply_text(t("err_parse_error"))
            except Exception:
                logger.debug(
                    "Could not send parse-failure reply to admin %s", admin_id, exc_info=True
                )
            return

        logger.info(
            "Processing admin %s (%s) action=%s on request %s",
            admin_id,
            admin_name,
            action,
            request_id,
        )

        # Verify admin authorization
        admin_user = await verify_bot_admin_authorization(int(admin_id))
        if not admin_user:
            logger.warning("Non-admin attempted action=%s on request %d", action, request_id)
            try:
                await update.message.reply_text(t("err_not_authorized"))
            except Exception:
                pass
            return

        # Execute the action using shared helper
        logger.info(
            "Calling %s_request for request %d (user_id: %s)",
            action,
            request_id,
            selected_user_id,
        )

        request, error = await _execute_admin_action(
            action=action,
            request_id=request_id,
            admin_user=admin_user,
            context=context,
            selected_user_id=selected_user_id,
        )

        if error:
            logger.warning("Action %s failed for request %d: %s", action, request_id, error)
            try:
                await update.message.reply_text(error)
            except Exception:
                logger.debug("Could not send error reply to admin %s", admin_id, exc_info=True)
            return

        # Send confirmation to admin
        logger.info(
            "%s successful for request %d, requester %s",
            action.capitalize(),
            request_id,
            request.user_telegram_id,
        )
        try:
            if action == "approve":
                if selected_user_id:
                    await update.message.reply_text(
                        t("msg_user_approved", user_id=selected_user_id)
                    )
                else:
                    await update.message.reply_text(t("msg_request_approved"))
            else:
                await update.message.reply_text(t("msg_request_rejected"))
        except Exception:
            logger.debug("Could not confirm %s to admin %s", action, admin_id, exc_info=True)

    except Exception as e:
        logger.error("Unhandled error in admin response handler: %s", e, exc_info=True)


async def handle_admin_callback(  # noqa: C901
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle inline button callback queries for approve/reject actions.

    Expected callback_data: "approve:<request_id>" or "reject:<request_id>".
    """
    try:
        cq = update.callback_query
        if not cq:
            return

        data = (cq.data or "").strip()
        parts = data.split(":")
        if len(parts) != 2:
            try:
                await cq.answer(t("err_invalid_action"))
            except Exception:
                logger.debug("Could not answer invalid callback", exc_info=True)
            return

        action, req_str = parts[0], parts[1]
        try:
            request_id = int(req_str)
        except Exception:
            try:
                await cq.answer(t("err_invalid_request_id"))
            except Exception:
                logger.debug("Could not answer invalid id", exc_info=True)
            return

        admin_id = str(cq.from_user.id)
        admin_name = cq.from_user.first_name or "Admin"

        # Verify admin authorization
        admin_user = await verify_bot_admin_authorization(int(admin_id))
        if not admin_user:
            logger.warning(
                "Non-admin attempted callback action=%s on request %d", action, request_id
            )
            try:
                await cq.answer(t("err_not_authorized"))
            except Exception:
                pass
            return

        # Validate action type
        if action not in ("approve", "reject"):
            try:
                await cq.answer(t("err_unknown_action"))
            except Exception:
                logger.debug("Could not answer unknown action", exc_info=True)
            return

        # Execute the action using shared helper
        request, error = await _execute_admin_action(
            action=action,
            request_id=request_id,
            admin_user=admin_user,
            context=context,
        )

        if error:
            try:
                await cq.answer(error)
            except Exception:
                logger.debug("Could not send error answer", exc_info=True)
            return

        # Send confirmation via callback answer and edit message
        try:
            if action == "approve":
                await cq.answer(t("msg_callback_approved"))
                await cq.edit_message_text(
                    t(
                        "msg_callback_approved_by",
                        request_id=request_id,
                        admin_name=admin_name,
                    )
                )
            else:
                await cq.answer(t("msg_callback_rejected"))
                await cq.edit_message_text(
                    t(
                        "msg_callback_rejected_by",
                        request_id=request_id,
                        admin_name=admin_name,
                    )
                )
        except Exception:
            logger.debug("Failed to edit/answer callback after %s", action, exc_info=True)

    except Exception as e:
        logger.error("Unhandled error in callback handler: %s", e, exc_info=True)


__all__ = ["handle_admin_response", "handle_admin_callback"]
