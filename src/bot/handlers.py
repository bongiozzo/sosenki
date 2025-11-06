"""Telegram bot handlers for command processing."""

import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from src.services import SessionLocal
from src.services.admin_service import AdminService
from src.services.notification_service import NotificationService
from src.services.request_service import RequestService

logger = logging.getLogger(__name__)


# /request command handler (T031)
async def handle_request_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /request command from client.

    Parses message, validates no pending request exists, stores request,
    sends confirmation to client and notification to admin.

    T031, T034, T035: Implement request handler with logging and error handling
    """
    try:
        # Extract message parts
        if not update.message or not update.message.text:
            logger.warning("Received /request without message text")
            await update.message.reply_text(
                "Please include your request message with /request"
            )
            return

        # Parse: /request <message>
        text_parts = update.message.text.split(maxsplit=1)
        if len(text_parts) < 2:
            logger.warning("Received /request without request message from user %s",
                          update.message.from_user.id)
            await update.message.reply_text(
                "Usage: /request <your message>"
            )
            return

        request_message = text_parts[1]
        client_id = str(update.message.from_user.id)
        client_name = update.message.from_user.first_name or "User"

        # T034: Log request submission attempt
        logger.info("Processing /request from client %s (%s): %s",
                   client_id, client_name, request_message[:50])

        # T028: Use RequestService to create request (validates no duplicate)
        db = SessionLocal()
        try:
            request_service = RequestService(db)
            new_request = await request_service.create_request(
                user_telegram_id=client_id,
                request_message=request_message
            )

            if not new_request:
                # T035: Handle duplicate pending request
                logger.warning("Duplicate pending request from client %s", client_id)
                await update.message.reply_text(
                    "You already have a pending request. Please wait for admin review."
                )
                return

            # T029: Send confirmation to client
            notification_service = NotificationService(context.application)
            await notification_service.send_confirmation_to_client(
                client_id=client_id
            )
            logger.info("Sent confirmation to client %s", client_id)

            # T030: Send admin notification
            try:
                await notification_service.send_notification_to_admin(
                    request_id=new_request.id,
                    client_id=client_id,
                    client_name=client_name,
                    request_message=request_message
                )
                logger.info("Sent admin notification for request %d", new_request.id)
            except Exception as e:
                logger.error("Failed to send admin notification: %s", e)
                # Don't fail the handler if admin notification fails

        finally:
            db.close()

    except Exception as e:
        # T035: Handle and log errors
        logger.error("Error processing /request: %s", e, exc_info=True)
        try:
            await update.message.reply_text(
                "An error occurred processing your request. Please try again."
            )
        except Exception as reply_error:
            logger.error("Failed to send error reply: %s", reply_error)


# Admin approval handler (T043)
async def handle_admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin approval response.

    Updates request status, sends welcome message to client,
    confirms action to admin.

    T043, T045, T046: Implement approval handler with logging and error handling
    """
    try:
        # Extract admin ID
        if not update.message or not update.message.from_user:
            logger.warning("Received approval without message or user info")
            return

        admin_id = str(update.message.from_user.id)
        admin_name = update.message.from_user.first_name or "Admin"

        # T046: Validate message is "Approve"
        if not update.message.text or "approve" not in update.message.text.lower():
            logger.warning("Received non-approval message from admin %s", admin_id)
            await update.message.reply_text("Please use /approve or reply with 'Approve'")
            return

        # Extract request ID from reply_to_message (if this is a reply)
        if not update.message.reply_to_message:
            logger.warning("Approval without reply_to_message from admin %s", admin_id)
            await update.message.reply_text("Please reply to a request notification")
            return

        # T045: Log approval received
        logger.info("Processing approval from admin %s (%s)",
                   admin_id, admin_name)

        # Parse request ID from the original message text
        # Expected format: "Request #123: Name (Client ID: 456) - 'message'"
        reply_text = update.message.reply_to_message.text or ""
        try:
            # Extract ID from message like "Request #123" (with or without HTML tags)
            # Handles both plain text and HTML formatted messages
            match = re.search(r"Request\s*#\s*(\d+)", reply_text)
            if match:
                request_id = int(match.group(1))
            else:
                raise ValueError("Message format not recognized - could not find 'Request #<id>'")
        except (ValueError, IndexError) as e:
            logger.warning("Could not parse request ID from message: %s (error: %s)", reply_text, e)
            await update.message.reply_text("Could not parse request ID from message")
            return

        # T043: Use AdminService to approve request
        db = SessionLocal()
        try:
            admin_service = AdminService(db)
            request = await admin_service.approve_request(
                request_id=request_id,
                admin_telegram_id=admin_id
            )

            if not request:
                # T046: Handle request not found
                logger.warning("Request %d not found for approval", request_id)
                await update.message.reply_text("Request not found")
                return

            # T041: Send welcome message to client
            notification_service = NotificationService(context.application)
            await notification_service.send_welcome_message(
                client_id=request.user_telegram_id
            )
            logger.info("Sent welcome message to client %s",
                       request.user_telegram_id)

            # Send confirmation to admin
            await update.message.reply_text("✅ Request approved and client notified")
            logger.info("Approval confirmed to admin %s for request %d",
                       admin_id, request_id)

        except Exception as e:
            # T046: Handle database errors
            logger.error("Error processing approval: %s", e, exc_info=True)
            await update.message.reply_text("Error processing approval")
        finally:
            db.close()

    except Exception as e:
        logger.error("Error in approval handler: %s", e, exc_info=True)


# Admin rejection handler (T051)
async def handle_admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin rejection response.

    Updates request status, sends rejection message to client,
    confirms action to admin.

    T051, T053, T054: Implement rejection handler with logging and error handling
    """
    try:
        # Extract admin ID
        if not update.message or not update.message.from_user:
            logger.warning("Received rejection without message or user info")
            return

        admin_id = str(update.message.from_user.id)
        admin_name = update.message.from_user.first_name or "Admin"

        # T054: Validate message is "Reject"
        if not update.message.text or "reject" not in update.message.text.lower():
            logger.warning("Received non-rejection message from admin %s", admin_id)
            await update.message.reply_text("Please use /reject or reply with 'Reject'")
            return

        # Extract request ID from reply_to_message (if this is a reply)
        if not update.message.reply_to_message:
            logger.warning("Rejection without reply_to_message from admin %s", admin_id)
            await update.message.reply_text("Please reply to a request notification")
            return

        # T053: Log rejection received
        logger.info("Processing rejection from admin %s (%s)",
                   admin_id, admin_name)

        # Parse request ID from the original message text
        # Expected format: "Request #123: Name (Client ID: 456) - 'message'"
        reply_text = update.message.reply_to_message.text or ""
        try:
            # Extract ID from message like "Request #123" (with or without HTML tags)
            # Handles both plain text and HTML formatted messages
            match = re.search(r"Request\s*#\s*(\d+)", reply_text)
            if match:
                request_id = int(match.group(1))
            else:
                raise ValueError("Message format not recognized - could not find 'Request #<id>'")
        except (ValueError, IndexError) as e:
            logger.warning("Could not parse request ID from message: %s (error: %s)", reply_text, e)
            await update.message.reply_text("Could not parse request ID from message")
            return

        # T051: Use AdminService to reject request
        db = SessionLocal()
        try:
            admin_service = AdminService(db)
            request = await admin_service.reject_request(
                request_id=request_id,
                admin_telegram_id=admin_id
            )

            if not request:
                # T054: Handle request not found
                logger.warning("Request %d not found for rejection", request_id)
                await update.message.reply_text("Request not found")
                return

            # T050: Send rejection message to client
            notification_service = NotificationService(context.application)
            await notification_service.send_rejection_message(
                client_id=request.user_telegram_id
            )
            logger.info("Sent rejection message to client %s",
                       request.user_telegram_id)

            # Send confirmation to admin
            await update.message.reply_text("✅ Request rejected and client notified")
            logger.info("Rejection confirmed to admin %s for request %d",
                       admin_id, request_id)

        except Exception as e:
            # T054: Handle database errors
            logger.error("Error processing rejection: %s", e, exc_info=True)
            await update.message.reply_text("Error processing rejection")
        finally:
            db.close()

    except Exception as e:
        logger.error("Error in rejection handler: %s", e, exc_info=True)


__all__ = [
    "handle_request_command",
    "handle_admin_approve",
    "handle_admin_reject",
    "handle_admin_response",
    "handle_admin_callback",
]


async def handle_admin_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Universal admin response handler.

    This handles both Approve and Reject replies to request notifications.
    The handler validates the reply, extracts the request id from the
    replied-to notification text, and then performs approve or reject
    actions atomically.
    """
    try:
        if not update.message or not update.message.from_user:
            logger.warning("Received admin response without message or user info")
            return

        admin_id = str(update.message.from_user.id)
        admin_name = update.message.from_user.first_name or "Admin"

        # Must be a reply to the original notification
        if not update.message.reply_to_message:
            logger.warning("Admin response without reply_to_message from %s", admin_id)
            try:
                await update.message.reply_text("Please reply to a request notification with 'Approve' or 'Reject'")
            except Exception:
                logger.debug("Could not send reply_text to admin %s", admin_id, exc_info=True)
            return

        text = (update.message.text or "").strip()
        text_lower = text.lower()

        # Determine action
        if "approve" in text_lower:
            action = "approve"
        elif "reject" in text_lower:
            action = "reject"
        else:
            logger.warning("Received non-action admin message from %s: %s", admin_id, text)
            try:
                await update.message.reply_text("Please reply with 'Approve' or 'Reject' to the request notification")
            except Exception:
                logger.debug("Could not send instruction reply to admin %s", admin_id, exc_info=True)
            return

        # Parse request id from the replied-to message
        # Handle both HTML format with tags (<b>Request #{id}</b>) and plain text format (Request #{id}:)
        reply_text = update.message.reply_to_message.text or ""
        try:
            # Use regex to find Request #<id> in any format (HTML or plain text)

            match = re.search(r'Request #(\d+)', reply_text)
            if match:
                request_id = int(match.group(1))
            else:
                raise ValueError("Message format not recognized - could not find 'Request #<id>'")
        except (ValueError, IndexError) as e:
            logger.warning("Could not parse request ID from message: %s (error: %s)", reply_text, e)
            try:
                await update.message.reply_text("Could not parse request ID from message")
            except Exception:
                logger.debug("Could not send parse-failure reply to admin %s", admin_id, exc_info=True)
            return

        logger.info("Processing admin %s (%s) action=%s on request %s", admin_id, admin_name, action, request_id)

        db = SessionLocal()
        try:
            admin_service = AdminService(db)

            if action == "approve":
                logger.info("Calling approve_request for request %d", request_id)
                request = await admin_service.approve_request(request_id=request_id, admin_telegram_id=admin_id)
                if not request:
                    logger.warning("Request %d not found for approval", request_id)
                    try:
                        await update.message.reply_text("Request not found")
                    except Exception:
                        logger.debug("Could not send 'not found' reply for approval to admin %s", admin_id, exc_info=True)
                    return

                logger.info("Approval successful, sending welcome message to client %s", request.user_telegram_id)
                notification_service = NotificationService(context.application)
                await notification_service.send_welcome_message(client_id=request.user_telegram_id)
                try:
                    await update.message.reply_text("✅ Request approved and client notified")
                except Exception:
                    logger.debug("Could not confirm approval to admin %s", admin_id, exc_info=True)

            else:  # reject
                logger.info("Calling reject_request for request %d", request_id)
                request = await admin_service.reject_request(request_id=request_id, admin_telegram_id=admin_id)
                if not request:
                    logger.warning("Request %d not found for rejection", request_id)
                    try:
                        await update.message.reply_text("Request not found")
                    except Exception:
                        logger.debug("Could not send 'not found' reply for rejection to admin %s", admin_id, exc_info=True)
                    return

                logger.info("Rejection successful, sending rejection message to client %s", request.user_telegram_id)
                notification_service = NotificationService(context.application)
                await notification_service.send_rejection_message(client_id=request.user_telegram_id)
                try:
                    await update.message.reply_text("✅ Request rejected and client notified")
                except Exception:
                    logger.debug("Could not confirm rejection to admin %s", admin_id, exc_info=True)

        except Exception as e:
            logger.error("Error processing admin action %s on request %s: %s", action, request_id, e, exc_info=True)
            try:
                await update.message.reply_text("Error processing request response")
            except Exception:
                logger.debug("Could not send error reply to admin %s", admin_id, exc_info=True)
        finally:
            db.close()

    except Exception as e:
        logger.error("Unhandled error in admin response handler: %s", e, exc_info=True)


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
                await cq.answer("Invalid action")
            except Exception:
                logger.debug("Could not answer invalid callback", exc_info=True)
            return

        action, req_str = parts[0], parts[1]
        try:
            request_id = int(req_str)
        except Exception:
            try:
                await cq.answer("Invalid request id")
            except Exception:
                logger.debug("Could not answer invalid id", exc_info=True)
            return

        admin_id = str(cq.from_user.id)
        admin_name = cq.from_user.first_name or "Admin"

        db = SessionLocal()
        try:
            admin_service = AdminService(db)

            if action == "approve":
                request = await admin_service.approve_request(request_id=request_id, admin_telegram_id=admin_id)
                if not request:
                    await cq.answer("Request not found")
                    return

                notification_service = NotificationService(context.application)
                await notification_service.send_welcome_message(client_id=request.user_telegram_id)
                try:
                    await cq.answer("Request approved")
                    await cq.edit_message_text(f"Request #{request_id} — ✅ Approved by {admin_name}")
                except Exception:
                    logger.debug("Failed to edit/answer callback after approval", exc_info=True)

            elif action == "reject":
                request = await admin_service.reject_request(request_id=request_id, admin_telegram_id=admin_id)
                if not request:
                    await cq.answer("Request not found")
                    return

                notification_service = NotificationService(context.application)
                await notification_service.send_rejection_message(client_id=request.user_telegram_id)
                try:
                    await cq.answer("Request rejected")
                    await cq.edit_message_text(f"Request #{request_id} — ❌ Rejected by {admin_name}")
                except Exception:
                    logger.debug("Failed to edit/answer callback after rejection", exc_info=True)

            else:
                try:
                    await cq.answer("Unknown action")
                except Exception:
                    logger.debug("Could not answer unknown action", exc_info=True)

        except Exception as e:
            logger.error("Error processing callback action %s on request %s: %s", action, request_id, e, exc_info=True)
            try:
                await cq.answer("Error processing action")
            except Exception:
                logger.debug("Could not send error answer", exc_info=True)
        finally:
            db.close()

    except Exception as e:
        logger.error("Unhandled error in callback handler: %s", e, exc_info=True)
