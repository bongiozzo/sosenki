"""Telegram bot handlers for command processing."""

import logging
import re

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes

from src.models.service_period import ServicePeriod
from src.models.user import User
from src.services import SessionLocal
from src.services.admin_service import AdminService
from src.services.localizer import t
from src.services.notification_service import NotificationService
from src.services.request_service import RequestService

logger = logging.getLogger(__name__)


# /start command handler
async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command.

    Sends welcome message to user.
    """
    try:
        if not update.message:
            logger.warning("Received /start without message")
            return

        await update.message.reply_text(t("labels.welcome"))
        logger.info("Sent welcome message to user %s", update.message.from_user.id)

    except Exception as e:
        logger.error("Error in start command handler: %s", e, exc_info=True)


# /request command handler (T031)
async def handle_request_command(  # noqa: C901
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /request command from client.

    Parses message, validates no pending request exists, stores request,
    sends confirmation to client and notification to admin.

    T031, T034, T035: Implement request handler with logging and error handling

    /request can be sent with or without a message:
    - /request                   -> submits request with no message
    - /request Some message text -> submits request with message text
    """
    try:
        # Extract message parts
        if not update.message or not update.message.text:
            logger.warning("Received /request without message text")
            return

        # Check if message is from a group chat (group chats don't support WebAppInfo buttons)
        if update.message.chat.type in ["group", "supergroup"]:
            logger.info(
                "Received /request from group chat %s, rejecting with private message prompt",
                update.message.chat.id,
            )

            from src.bot.config import bot_config

            await update.message.reply_text(
                t("requests.group_chat_error", bot_name=bot_config.telegram_bot_name)
            )
            return

        # Parse: /request [message] (message is optional)
        text_parts = update.message.text.split(maxsplit=1)
        request_message = text_parts[1] if len(text_parts) > 1 else ""

        requester_id = update.message.from_user.id

        # Build requester identifier: prefer username, then first+last name, then phone, then user_id
        if update.message.from_user.username:
            requester_username = update.message.from_user.username
        elif update.message.from_user.first_name:
            if update.message.from_user.last_name:
                requester_username = (
                    f"{update.message.from_user.first_name} {update.message.from_user.last_name}"
                )
            else:
                requester_username = update.message.from_user.first_name
        elif update.message.from_user.phone_number:
            requester_username = update.message.from_user.phone_number
        else:
            requester_username = requester_id

        # T034: Log request submission attempt
        logger.info(
            "Processing /request from requester %s: %s",
            requester_id,
            request_message[:50] if request_message else "(no message)",
        )

        # T028: Use RequestService to create request (validates no duplicate)
        db = SessionLocal()
        try:
            # Check if user already exists with this telegram_id and is active
            existing_user = db.execute(
                select(User).where(User.telegram_id == requester_id)
            ).scalar_one_or_none()

            if existing_user and existing_user.is_active:
                logger.info("User %s (%s) already has access", requester_id, existing_user.name)

                from src.bot.config import bot_config

                keyboard = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text=t("bot.open_app"),
                                web_app=WebAppInfo(url=bot_config.mini_app_url),
                            )
                        ]
                    ]
                )

                await update.message.reply_text(t("bot.already_have_access"), reply_markup=keyboard)
                return

            request_service = RequestService(db)
            new_request = await request_service.create_request(
                user_telegram_id=requester_id,
                request_message=request_message,
                user_telegram_username=requester_username,
            )

            if not new_request:
                # T035: Handle duplicate pending request
                logger.warning("Duplicate pending request from requester %s", requester_id)
                await update.message.reply_text(t("bot.duplicate_request"))
                return

            # T029: Send confirmation to requester
            notification_service = NotificationService(context.application)
            await notification_service.send_confirmation_to_requester(requester_id=requester_id)
            logger.info("Sent confirmation to requester %s", requester_id)

            # T030: Send admin notification
            try:
                await notification_service.send_notification_to_admin(
                    request_id=new_request.id,
                    requester_id=requester_id,
                    requester_username=requester_username,
                    request_message=request_message,
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
            await update.message.reply_text(t("bot.error_processing"))
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

        admin_id = update.message.from_user.id
        admin_name = update.message.from_user.first_name or "Admin"

        # T046: Validate message is "Approve"
        if not update.message.text or "approve" not in update.message.text.lower():
            logger.warning("Received non-approval message from admin %s", admin_id)
            await update.message.reply_text(t("bot.please_approve_or_reject"))
            return

        # Extract request ID from reply_to_message (if this is a reply)
        if not update.message.reply_to_message:
            logger.warning("Approval without reply_to_message from admin %s", admin_id)
            await update.message.reply_text(t("bot.reply_to_notification"))
            return

        # T045: Log approval received
        logger.info("Processing approval from admin %s (%s)", admin_id, admin_name)

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
            await update.message.reply_text(t("bot.parse_error"))
            return

        # T043: Use AdminService to approve request
        db = SessionLocal()
        try:
            admin_service = AdminService(db)
            request = await admin_service.approve_request(
                request_id=request_id, admin_telegram_id=admin_id
            )

            if not request:
                # T046: Handle request not found
                logger.warning("Request %d not found for approval", request_id)
                await update.message.reply_text(t("bot.request_not_found"))
                return

            # T041: Send welcome message to requester
            notification_service = NotificationService(context.application)
            await notification_service.send_welcome_message(requester_id=request.user_telegram_id)
            logger.info("Sent welcome message to requester %s", request.user_telegram_id)

            # Send confirmation to admin
            await update.message.reply_text(t("bot.approval_confirmed"))
            logger.info("Approval confirmed to admin %s for request %d", admin_id, request_id)

        except Exception as e:
            # T046: Handle database errors
            logger.error("Error processing approval: %s", e, exc_info=True)
            await update.message.reply_text(t("bot.error_approval"))
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

        admin_id = update.message.from_user.id
        admin_name = update.message.from_user.first_name or "Admin"

        # T054: Validate message is "Reject"
        if not update.message.text or "reject" not in update.message.text.lower():
            logger.warning("Received non-rejection message from admin %s", admin_id)
            await update.message.reply_text(t("bot.please_reject"))
            return

        # Extract request ID from reply_to_message (if this is a reply)
        if not update.message.reply_to_message:
            logger.warning("Rejection without reply_to_message from admin %s", admin_id)
            await update.message.reply_text(t("bot.reply_to_notification"))
            return

        # T053: Log rejection received
        logger.info("Processing rejection from admin %s (%s)", admin_id, admin_name)

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
            await update.message.reply_text(t("bot.parse_error"))
            return

        # T051: Use AdminService to reject request
        db = SessionLocal()
        try:
            admin_service = AdminService(db)
            request = await admin_service.reject_request(
                request_id=request_id, admin_telegram_id=admin_id
            )

            if not request:
                # T054: Handle request not found
                logger.warning("Request %d not found for rejection", request_id)
                await update.message.reply_text(t("bot.request_not_found"))
                return

            # T050: Send rejection message to requester
            notification_service = NotificationService(context.application)
            await notification_service.send_rejection_message(requester_id=request.user_telegram_id)
            logger.info("Sent rejection message to requester %s", request.user_telegram_id)

            # Send confirmation to admin
            await update.message.reply_text(t("bot.rejection_confirmed"))
            logger.info("Rejection confirmed to admin %s for request %d", admin_id, request_id)

        except Exception as e:
            # T054: Handle database errors
            logger.error("Error processing rejection: %s", e, exc_info=True)
            await update.message.reply_text(t("bot.error_rejection"))
        finally:
            db.close()

    except Exception as e:
        logger.error("Error in rejection handler: %s", e, exc_info=True)


__all__ = [
    "handle_start_command",
    "handle_request_command",
    "handle_admin_approve",
    "handle_admin_reject",
    "handle_admin_response",
    "handle_admin_callback",
]


async def handle_admin_response(  # noqa: C901
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
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
        admin_name = update.message.from_user.username or "Admin"

        # Must be a reply to the original notification
        if not update.message.reply_to_message:
            logger.warning("Admin response without reply_to_message from %s", admin_id)
            try:
                await update.message.reply_text(t("bot.reply_approve_or_reject"))
            except Exception:
                logger.debug("Could not send reply_text to admin %s", admin_id, exc_info=True)
            return

        text = (update.message.text or "").strip()
        text_lower = text.lower()

        # Check if input is a number (user ID selection)
        selected_user_id = None
        try:
            if text.isdigit():
                selected_user_id = int(text)
                action = "approve"  # Numeric selection always means approve
                logger.info("User ID selection detected: %d", selected_user_id)
            elif "approve" in text_lower:
                action = "approve"
            elif "reject" in text_lower:
                action = "reject"
            else:
                logger.warning("Received non-action admin message from %s: %s", admin_id, text)
                try:
                    await update.message.reply_text(t("bot.reply_with_id_or_action"))
                except Exception:
                    logger.debug(
                        "Could not send instruction reply to admin %s", admin_id, exc_info=True
                    )
                return
        except ValueError:
            logger.warning("Could not parse admin response from %s: %s", admin_id, text)
            try:
                await update.message.reply_text(t("bot.invalid_response"))
            except Exception:
                logger.debug(
                    "Could not send parse error reply to admin %s", admin_id, exc_info=True
                )
            return

        # Parse request id from the replied-to message
        # Handle both HTML format with tags (<b>Request #{id}</b>) and plain text format (Request #{id}:)
        reply_text = update.message.reply_to_message.text or ""
        try:
            # Use regex to find Request #<id> in any format (HTML or plain text)

            match = re.search(r"Request #(\d+)", reply_text)
            if match:
                request_id = int(match.group(1))
            else:
                raise ValueError("Message format not recognized - could not find 'Request #<id>'")
        except (ValueError, IndexError) as e:
            logger.warning("Could not parse request ID from message: %s (error: %s)", reply_text, e)
            try:
                await update.message.reply_text(t("bot.parse_error"))
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

        db = SessionLocal()
        try:
            admin_service = AdminService(db)

            if action == "approve":
                logger.info(
                    "Calling approve_request for request %d (user_id: %s)",
                    request_id,
                    selected_user_id,
                )

                request = await admin_service.approve_request(
                    request_id=request_id,
                    admin_telegram_id=admin_id,
                    selected_user_id=selected_user_id,
                )
                if not request:
                    logger.warning("Request %d not found for approval", request_id)
                    try:
                        await update.message.reply_text(t("bot.request_not_found_or_invalid"))
                    except Exception:
                        logger.debug(
                            "Could not send 'not found' reply for approval to admin %s",
                            admin_id,
                            exc_info=True,
                        )
                    return

                logger.info(
                    "Approval successful, sending welcome message to requester %s",
                    request.user_telegram_id,
                )
                notification_service = NotificationService(context.application)
                await notification_service.send_welcome_message(
                    requester_id=request.user_telegram_id
                )
                try:
                    if selected_user_id:
                        await update.message.reply_text(
                            t("bot.user_approved_with_id", user_id=selected_user_id)
                        )
                    else:
                        await update.message.reply_text(t("bot.approval_confirmed"))
                except Exception:
                    logger.debug("Could not confirm approval to admin %s", admin_id, exc_info=True)

            else:  # reject
                logger.info("Calling reject_request for request %d", request_id)
                request = await admin_service.reject_request(
                    request_id=request_id, admin_telegram_id=admin_id
                )
                if not request:
                    logger.warning("Request %d not found for rejection", request_id)
                    try:
                        await update.message.reply_text(t("bot.request_not_found"))
                    except Exception:
                        logger.debug(
                            "Could not send 'not found' reply for rejection to admin %s",
                            admin_id,
                            exc_info=True,
                        )
                    return

                logger.info(
                    "Rejection successful, sending rejection message to client %s",
                    request.user_telegram_id,
                )
                notification_service = NotificationService(context.application)
                await notification_service.send_rejection_message(
                    client_id=request.user_telegram_id
                )
                try:
                    await update.message.reply_text(t("bot.rejection_confirmed"))
                except Exception:
                    logger.debug("Could not confirm rejection to admin %s", admin_id, exc_info=True)

        except Exception as e:
            logger.error(
                "Error processing admin action %s on request %s: %s",
                action,
                request_id,
                e,
                exc_info=True,
            )
            try:
                await update.message.reply_text(t("bot.error_processing_response"))
            except Exception:
                logger.debug("Could not send error reply to admin %s", admin_id, exc_info=True)
        finally:
            db.close()

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
                await cq.answer(t("bot.invalid_action"))
            except Exception:
                logger.debug("Could not answer invalid callback", exc_info=True)
            return

        action, req_str = parts[0], parts[1]
        try:
            request_id = int(req_str)
        except Exception:
            try:
                await cq.answer(t("bot.invalid_request_id"))
            except Exception:
                logger.debug("Could not answer invalid id", exc_info=True)
            return

        admin_id = str(cq.from_user.id)
        admin_name = cq.from_user.first_name or "Admin"

        db = SessionLocal()
        try:
            admin_service = AdminService(db)

            if action == "approve":
                request = await admin_service.approve_request(
                    request_id=request_id, admin_telegram_id=admin_id
                )
                if not request:
                    await cq.answer(t("bot.request_not_found"))
                    return

                notification_service = NotificationService(context.application)
                await notification_service.send_welcome_message(
                    requester_id=request.user_telegram_id
                )
                try:
                    await cq.answer(t("bot.callback_approved"))
                    await cq.edit_message_text(
                        t("bot.callback_approved_by", request_id=request_id, admin_name=admin_name)
                    )
                except Exception:
                    logger.debug("Failed to edit/answer callback after approval", exc_info=True)

            elif action == "reject":
                request = await admin_service.reject_request(
                    request_id=request_id, admin_telegram_id=admin_id
                )
                if not request:
                    await cq.answer(t("bot.request_not_found"))
                    return

                notification_service = NotificationService(context.application)
                await notification_service.send_rejection_message(
                    requester_id=request.user_telegram_id
                )
                try:
                    await cq.answer(t("bot.callback_rejected"))
                    await cq.edit_message_text(
                        t("bot.callback_rejected_by", request_id=request_id, admin_name=admin_name)
                    )
                except Exception:
                    logger.debug("Failed to edit/answer callback after rejection", exc_info=True)

            else:
                try:
                    await cq.answer(t("bot.unknown_action"))
                except Exception:
                    logger.debug("Could not answer unknown action", exc_info=True)

        except Exception as e:
            logger.error(
                "Error processing callback action %s on request %s: %s",
                action,
                request_id,
                e,
                exc_info=True,
            )
            try:
                await cq.answer(t("bot.error_callback"))
            except Exception:
                logger.debug("Could not send error answer", exc_info=True)
        finally:
            db.close()

    except Exception as e:
        logger.error("Unhandled error in callback handler: %s", e, exc_info=True)


# Electricity bills management handlers (T050+)
async def handle_electricity_bills_command(  # noqa: C901
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Start electricity bills management workflow.

    Admin command to interactively calculate and create shared electricity bills.
    Entry point for multi-step conversation.

    T050: Implement electricity bills admin command

    Returns:
        Conversation state for next step (SELECT_PERIOD)
    """
    try:
        if not update.message or not update.message.from_user:
            logger.warning("Received electricity command without message or user")
            return -1  # End conversation

        # TODO: Add admin authorization check here
        # For MVP, assume admin access (will be added in future)

        db = SessionLocal()

        try:
            # Query open service periods
            open_periods = db.query(ServicePeriod).filter(
                ServicePeriod.status == "open"
            ).order_by(ServicePeriod.start_date.desc()).all()

            # Build inline buttons for period selection
            buttons = []
            for period in open_periods[:5]:  # Limit to 5 recent periods
                buttons.append(
                    [InlineKeyboardButton(
                        f"📅 {period.name}",
                        callback_data=f"elec_period:{period.id}"
                    )]
                )

            # Add "Create New" button
            buttons.append(
                [InlineKeyboardButton(
                    t("electricity.new_period"),
                    callback_data="elec_period:new"
                )]
            )

            keyboard = InlineKeyboardMarkup(buttons)

            await update.message.reply_text(
                t("electricity.select_period"),
                reply_markup=keyboard,
            )

            logger.info("Electricity bills workflow started for user %s", update.message.from_user.id)

            # Store initial context
            context.user_data["electricity_admin_id"] = update.message.from_user.id

            return 1  # Next state: SELECT_PERIOD (callback handler will advance)

        finally:
            db.close()

    except Exception as e:
        logger.error("Error starting electricity bills workflow: %s", e, exc_info=True)
        await update.message.reply_text(t("bot.error_processing"))
        return -1  # End conversation


async def handle_electricity_period_selection(  # noqa: C901
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle service period selection for electricity bills.

    User selects existing period or chooses to create new one.
    """
    try:
        cq = update.callback_query
        if not cq or not cq.data:
            logger.warning("Received period selection callback without data")
            return -1

        await cq.answer()

        db = SessionLocal()

        try:
            if cq.data == "elec_period:new":
                # Ask for start date
                await cq.edit_message_text(t("electricity.start_date_prompt"))
                context.user_data["electricity_create_new"] = True
                return 2  # INPUT_START_DATE
            else:
                # Extract period ID
                try:
                    period_id = int(cq.data.split(":")[1])
                except (IndexError, ValueError):
                    logger.warning("Invalid period callback data: %s", cq.data)
                    await cq.edit_message_text(t("bot.error_processing"))
                    return -1

                # Fetch period
                period = db.query(ServicePeriod).filter(ServicePeriod.id == period_id).first()
                if not period:
                    logger.warning("Period %d not found", period_id)
                    await cq.edit_message_text(t("bot.error_processing"))
                    return -1

                # Store selected period
                context.user_data["electricity_period_id"] = period_id
                context.user_data["electricity_period_name"] = period.name

                # Ask for electricity_start (with default from period.electricity_end if available)
                default_start = period.electricity_end if period.electricity_end else "?"
                prompt = f"{t('electricity.meter_start_label')}\n\n(Предыдущее значение: {default_start})"
                await cq.edit_message_text(prompt)

                return 3  # INPUT_ELECTRICITY_START

        finally:
            db.close()

    except Exception as e:
        logger.error("Error in period selection: %s", e, exc_info=True)
        try:
            await update.callback_query.edit_message_text(t("bot.error_processing"))
        except Exception:
            logger.debug("Could not edit message after error", exc_info=True)
        return -1


async def handle_electricity_start_date_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle start date input for new service period."""
    try:
        if not update.message or not update.message.text:
            return 2

        text = update.message.text.strip()

        # Validate date format DD.MM.YYYY
        from datetime import datetime
        try:
            start_date = datetime.strptime(text, "%d.%m.%Y").date()
        except ValueError:
            await update.message.reply_text(t("electricity.invalid_date_format"))
            return 2  # Re-ask

        context.user_data["electricity_start_date"] = start_date

        # Ask for end date
        await update.message.reply_text(t("electricity.end_date_prompt"))
        return 4  # INPUT_END_DATE

    except Exception as e:
        logger.error("Error in start date input: %s", e, exc_info=True)
        await update.message.reply_text(t("bot.error_processing"))
        return -1


async def handle_electricity_end_date_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle end date input for new service period."""
    try:
        if not update.message or not update.message.text:
            return 4

        text = update.message.text.strip()

        # Validate date format DD.MM.YYYY
        from datetime import datetime
        try:
            end_date = datetime.strptime(text, "%d.%m.%Y").date()
        except ValueError:
            await update.message.reply_text(t("electricity.invalid_date_format"))
            return 4  # Re-ask

        start_date = context.user_data.get("electricity_start_date")
        if end_date <= start_date:
            await update.message.reply_text(t("electricity.end_date_before_start"))
            return 4  # Re-ask

        context.user_data["electricity_end_date"] = end_date

        # Ask for electricity_start
        await update.message.reply_text(t("electricity.meter_start_label"))
        return 3  # INPUT_ELECTRICITY_START

    except Exception as e:
        logger.error("Error in end date input: %s", e, exc_info=True)
        await update.message.reply_text(t("bot.error_processing"))
        return -1


async def handle_electricity_meter_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle electricity meter start reading input."""
    try:
        if not update.message or not update.message.text:
            return 3

        text = update.message.text.strip()

        # Validate numeric input
        from decimal import Decimal, InvalidOperation
        try:
            electricity_start = Decimal(text.replace(",", "."))
            if electricity_start < 0:
                raise ValueError()
        except (InvalidOperation, ValueError):
            await update.message.reply_text(t("electricity.invalid_number"))
            return 3  # Re-ask

        context.user_data["electricity_start"] = electricity_start

        # Ask for electricity_end
        await update.message.reply_text(t("electricity.meter_end_label"))
        return 5  # INPUT_ELECTRICITY_END

    except Exception as e:
        logger.error("Error in meter start input: %s", e, exc_info=True)
        await update.message.reply_text(t("bot.error_processing"))
        return -1


async def handle_electricity_meter_end(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle electricity meter end reading input."""
    try:
        if not update.message or not update.message.text:
            return 5

        text = update.message.text.strip()

        # Validate numeric input
        from decimal import Decimal, InvalidOperation
        try:
            electricity_end = Decimal(text.replace(",", "."))
            if electricity_end < 0:
                raise ValueError()
        except (InvalidOperation, ValueError):
            await update.message.reply_text(t("electricity.invalid_number"))
            return 5  # Re-ask

        electricity_start = context.user_data.get("electricity_start")
        if electricity_end <= electricity_start:
            await update.message.reply_text(t("electricity.meter_end_less_than_start"))
            return 5  # Re-ask

        context.user_data["electricity_end"] = electricity_end

        # Ask for multiplier
        await update.message.reply_text(t("electricity.multiplier_label"))
        return 6  # INPUT_MULTIPLIER

    except Exception as e:
        logger.error("Error in meter end input: %s", e, exc_info=True)
        await update.message.reply_text(t("bot.error_processing"))
        return -1


async def handle_electricity_multiplier(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle electricity multiplier input."""
    try:
        if not update.message or not update.message.text:
            return 6

        text = update.message.text.strip()

        # Validate numeric input
        from decimal import Decimal, InvalidOperation
        try:
            multiplier = Decimal(text.replace(",", "."))
            if multiplier <= 0:
                raise ValueError()
        except (InvalidOperation, ValueError):
            await update.message.reply_text(t("electricity.invalid_number"))
            return 6  # Re-ask

        context.user_data["electricity_multiplier"] = multiplier

        # Ask for rate
        await update.message.reply_text(t("electricity.rate_label"))
        return 7  # INPUT_RATE

    except Exception as e:
        logger.error("Error in multiplier input: %s", e, exc_info=True)
        await update.message.reply_text(t("bot.error_processing"))
        return -1


async def handle_electricity_rate(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle electricity rate input."""
    try:
        if not update.message or not update.message.text:
            return 7

        text = update.message.text.strip()

        # Validate numeric input
        from decimal import Decimal, InvalidOperation
        try:
            rate = Decimal(text.replace(",", "."))
            if rate <= 0:
                raise ValueError()
        except (InvalidOperation, ValueError):
            await update.message.reply_text(t("electricity.invalid_number"))
            return 7  # Re-ask

        context.user_data["electricity_rate"] = rate

        # Ask for losses
        await update.message.reply_text(t("electricity.losses_label"))
        return 8  # INPUT_LOSSES

    except Exception as e:
        logger.error("Error in rate input: %s", e, exc_info=True)
        await update.message.reply_text(t("bot.error_processing"))
        return -1


async def handle_electricity_losses(  # noqa: C901
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle electricity losses input and calculate total cost."""
    try:
        if not update.message or not update.message.text:
            return 8

        text = update.message.text.strip()

        # Validate numeric input between 0 and 1
        from decimal import Decimal, InvalidOperation
        try:
            losses = Decimal(text.replace(",", "."))
            if losses < 0 or losses > 1:
                raise ValueError()
        except (InvalidOperation, ValueError):
            await update.message.reply_text(t("electricity.invalid_losses"))
            return 8  # Re-ask

        context.user_data["electricity_losses"] = losses

        # Calculate total electricity cost
        from src.services.electricity_service import ElectricityService

        db = SessionLocal()
        try:
            electricity_service = ElectricityService(db)

            start = context.user_data.get("electricity_start")
            end = context.user_data.get("electricity_end")
            multiplier = context.user_data.get("electricity_multiplier")
            rate = context.user_data.get("electricity_rate")

            total_cost = electricity_service.calculate_total_electricity(
                start, end, multiplier, rate, losses
            )

            context.user_data["electricity_total_cost"] = total_cost

            # Show calculation and ask for confirmation
            message = t("electricity.total_cost_calculated", amount=float(total_cost))

            buttons = [
                [
                    InlineKeyboardButton(t("common.next"), callback_data="elec_confirm:yes"),
                    InlineKeyboardButton(t("common.cancel"), callback_data="elec_confirm:no"),
                ]
            ]
            keyboard = InlineKeyboardMarkup(buttons)

            await update.message.reply_text(message, reply_markup=keyboard)

            return 9  # CONFIRM_CALCULATION

        finally:
            db.close()

    except Exception as e:
        logger.error("Error in losses input: %s", e, exc_info=True)
        await update.message.reply_text(t("bot.error_processing"))
        return -1


async def handle_electricity_confirm_calculation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle confirmation of electricity cost calculation."""
    try:
        cq = update.callback_query
        if not cq or not cq.data:
            return 9

        await cq.answer()

        if cq.data == "elec_confirm:no":
            await cq.edit_message_text(t("electricity.operation_cancelled"))
            return -1  # End conversation

        # Proceed to distribute costs among owners
        db = SessionLocal()
        try:
            from src.services.electricity_service import ElectricityService

            electricity_service = ElectricityService(db)

            period_id = context.user_data.get("electricity_period_id")
            total_cost = context.user_data.get("electricity_total_cost")

            # Get existing electricity bills sum
            personal_bills_sum = electricity_service.get_electricity_bills_for_period(period_id)

            # Calculate shared cost
            shared_cost = total_cost - personal_bills_sum

            context.user_data["electricity_personal_bills_sum"] = personal_bills_sum
            context.user_data["electricity_shared_cost"] = shared_cost

            # Fetch the service period
            period = db.query(ServicePeriod).filter(ServicePeriod.id == period_id).first()
            if not period:
                await cq.edit_message_text(t("bot.error_processing"))
                return -1

            # Distribute costs
            owner_shares = electricity_service.distribute_shared_costs(shared_cost, period)

            context.user_data["electricity_owner_shares"] = owner_shares

            # Show distribution message
            distribution_text = t(
                "electricity.existing_bills_sum",
                personal_sum=float(personal_bills_sum),
                difference=float(shared_cost),
            )

            await cq.edit_message_text(distribution_text)

            # Now show the proposed bills table
            return await show_electricity_bills_table(update, context)

        finally:
            db.close()

    except Exception as e:
        logger.error("Error in calculation confirmation: %s", e, exc_info=True)
        try:
            await update.callback_query.edit_message_text(t("bot.error_processing"))
        except Exception:
            pass
        return -1


async def show_electricity_bills_table(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Display proposed electricity bills table and ask for confirmation."""
    try:
        owner_shares = context.user_data.get("electricity_owner_shares", [])

        # Build bills table
        bills_text = ""
        for share in owner_shares:
            bills_text += (
                f"• {share.user_name}: "
                f"{share.total_share_weight:.2f} → "
                f"{share.calculated_bill_amount:.2f} ₽\n"
            )

        message = t("electricity.confirm_bills_message", bills_table=bills_text)

        buttons = [
            [
                InlineKeyboardButton(t("electricity.create_bills"), callback_data="elec_bills:create"),
                InlineKeyboardButton(t("common.cancel"), callback_data="elec_bills:cancel"),
            ]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        if update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=keyboard)
        else:
            await update.message.reply_text(message, reply_markup=keyboard)

        return 10  # CONFIRM_BILLS

    except Exception as e:
        logger.error("Error showing bills table: %s", e, exc_info=True)
        return -1


async def handle_electricity_create_bills(  # noqa: C901
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Create shared electricity bills in the database."""
    try:
        cq = update.callback_query
        if not cq or not cq.data:
            return 10

        await cq.answer()

        if cq.data == "elec_bills:cancel":
            await cq.edit_message_text(t("electricity.operation_cancelled"))
            return -1  # End conversation

        # Create bills
        db = SessionLocal()
        try:
            owner_shares = context.user_data.get("electricity_owner_shares", [])
            period_id = context.user_data.get("electricity_period_id")

            if not owner_shares or not period_id:
                await cq.edit_message_text(t("bot.error_processing"))
                return -1

            # Create bills for each owner
            from src.models.account import Account
            from src.models.bill import Bill, BillType

            bills_created = 0

            for share in owner_shares:
                # Find account for this user
                account = (
                    db.query(Account)
                    .filter(Account.user_id == share.user_id, Account.account_type == "owner")
                    .first()
                )

                if account:
                    bill = Bill(
                        service_period_id=period_id,
                        account_id=account.id,
                        property_id=None,
                        bill_type=BillType.SHARED_ELECTRICITY,
                        bill_amount=share.calculated_bill_amount,
                    )
                    db.add(bill)
                    bills_created += 1

            db.commit()

            # Confirm success
            message = t("electricity.bills_created", count=bills_created)
            await cq.edit_message_text(message)

            logger.info("Created %d shared electricity bills for period %d", bills_created, period_id)

            return -1  # End conversation

        except Exception as e:
            db.rollback()
            logger.error("Error creating bills: %s", e, exc_info=True)
            await cq.edit_message_text(t("bot.error_processing"))
            return -1

        finally:
            db.close()

    except Exception as e:
        logger.error("Error in create bills handler: %s", e, exc_info=True)
        try:
            await update.callback_query.edit_message_text(t("bot.error_processing"))
        except Exception:
            pass
        return -1

