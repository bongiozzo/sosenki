"""Contract tests for admin handlers.

T036-T038: Contract tests for admin approval flow.
T047-T049: Contract tests for admin rejection flow (placeholders).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from src.api import webhook as webhook_module
from src.models.access_request import AccessRequest, RequestStatus
from src.services import SessionLocal


@pytest.fixture(autouse=True)
def cleanup_db():
    """Clean up database before and after each test."""
    db = SessionLocal()
    try:
        # Try to delete, but ignore if table doesn't exist
        db.execute(delete(AccessRequest))
        db.commit()
    except Exception:
        # Table may not exist if migrations haven't run
        db.rollback()
    finally:
        db.close()

    yield

    db = SessionLocal()
    try:
        db.execute(delete(AccessRequest))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


@pytest.fixture
def mock_bot():
    """Create a mock bot with async methods."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def client(mock_bot):
    """FastAPI test client with mocked bot."""
    with patch("telegram.Update.de_json") as mock_de_json:

        def de_json_side_effect(data, bot_instance):
            """Convert dict to Update object."""
            if data and "message" in data:
                update = MagicMock()
                update.message = MagicMock()
                update.message.text = data["message"]["text"]
                update.message.from_user = MagicMock()
                update.message.from_user.id = data["message"]["from"]["id"]
                update.message.from_user.first_name = data["message"]["from"].get(
                    "first_name", "Admin"
                )
                update.message.from_user.username = data["message"]["from"].get("username", None)
                # Handle reply_to_message
                update.message.reply_to_message = None
                if "reply_to_message" in data["message"]:
                    rtm = MagicMock()
                    rtm.text = data["message"]["reply_to_message"].get("text", "")
                    update.message.reply_to_message = rtm
                update.message.chat = MagicMock()
                update.message.chat.id = data["message"]["from"]["id"]
                update.message.chat.type = data["message"].get("chat", {}).get("type", "private")
                update.message.reply_text = AsyncMock()
                return update
            return None

        mock_de_json.side_effect = de_json_side_effect

        mock_app = MagicMock()
        mock_app.bot = mock_bot
        mock_app.process_update = AsyncMock()

        async def process_update_impl(update):
            """Process update through the handler."""
            if update.message and update.message.text:
                from src.bot.handlers import handle_admin_response

                ctx = MagicMock()
                ctx.application = mock_app
                ctx.bot_data = {}

                # Use the unified admin response handler
                await handle_admin_response(update, ctx)

        mock_app.process_update.side_effect = process_update_impl

        webhook_module._bot_app = mock_app

        yield TestClient(webhook_module.app)

        webhook_module._bot_app = None


class TestAdminHandlers:
    """Contract tests for admin approval/rejection handlers."""

    def _create_request_in_db(self, client_id: int, message: str = "Help needed"):
        """Helper to create a pending request in database."""
        db = SessionLocal()
        try:
            request = AccessRequest(
                user_telegram_id=str(client_id),
                request_message=message,
                status=RequestStatus.PENDING,
            )
            db.add(request)
            db.commit()
            db.refresh(request)
            return request
        finally:
            db.close()

    def test_admin_approval_handler(self, client, mock_bot):
        """Test admin approval response handler (T036).

        Contract: POST /webhook/telegram with "Approve" reply → returns 200,
        request status updated to approved, client receives welcome message.
        """
        # Setup: Create a pending request
        client_id = 123456789
        admin_id = 987654321
        request = self._create_request_in_db(client_id, "Emergency help")

        # Create Telegram Update for admin approval
        update_json = {
            "update_id": 100,
            "message": {
                "message_id": 100,
                "date": int(datetime.now(timezone.utc).timestamp()),
                "chat": {"id": admin_id, "type": "private"},
                "from": {"id": admin_id, "is_bot": False, "first_name": "Admin"},
                "text": "Approve",
                "reply_to_message": {
                    "message_id": 50,
                    "from": {"id": 777, "is_bot": True},
                    "text": f"<b>Request #{request.id}</b>\n\n<a href='tg://user?id={client_id}'>Test</a> (ID: {client_id})\n\n<b>Message:</b>\nEmergency help\n\nReply with 'Approve' or 'Reject' or use the buttons below",
                },
            },
        }

        # Send approval update
        response = client.post("/webhook/telegram", json=update_json)

        # Verify endpoint returns 200
        assert response.status_code == 200
        assert response.json()["ok"] is True

        # Verify request status updated in database
        db = SessionLocal()
        try:
            updated_request = db.query(AccessRequest).filter(AccessRequest.id == request.id).first()
            assert updated_request is not None
            assert updated_request.status == RequestStatus.APPROVED
            assert updated_request.admin_telegram_id == str(admin_id)
        finally:
            db.close()

    def test_approval_with_invalid_request(self, client, mock_bot):
        """Test approval when request doesn't exist (T037).

        Contract: POST /webhook/telegram with "Approve" when request doesn't exist
        → returns 200, admin receives error "Request not found".
        """
        admin_id = 987654321

        # Create update with approval but no valid request ID
        update_json = {
            "update_id": 101,
            "message": {
                "message_id": 101,
                "date": int(datetime.now(timezone.utc).timestamp()),
                "chat": {"id": admin_id, "type": "private"},
                "from": {"id": admin_id, "is_bot": False, "first_name": "Admin"},
                "text": "Approve",
                "reply_to_message": {
                    "message_id": 99,
                    "from": {"id": 777, "is_bot": True},
                    "text": "<b>Request #99999</b>\n\n<a href='tg://user?id=999999'>Unknown</a> (ID: 999999)\n\n<b>Message:</b>\nTest\n\nReply with 'Approve' or 'Reject' or use the buttons below",
                },
            },
        }

        # Send approval update
        response = client.post("/webhook/telegram", json=update_json)

        # Verify endpoint returns 200
        assert response.status_code == 200
        assert response.json()["ok"] is True

        # Verify no requests in database (invalid request, nothing changed)
        db = SessionLocal()
        try:
            all_requests = db.query(AccessRequest).all()
            assert len(all_requests) == 0
        finally:
            db.close()

    def test_admin_rejection_handler(self, client, mock_bot):
        """Test admin rejection response handler (T047).

        Contract: POST /webhook/telegram with "Reject" reply → returns 200,
        request status updated to rejected, client receives rejection message.
        """
        # Setup: Create a pending request
        client_id = 111222333
        admin_id = 987654321
        request = self._create_request_in_db(client_id, "Suspicious request")

        # Create Telegram Update for admin rejection
        update_json = {
            "update_id": 200,
            "message": {
                "message_id": 200,
                "date": int(datetime.now(timezone.utc).timestamp()),
                "chat": {"id": admin_id, "type": "private"},
                "from": {"id": admin_id, "is_bot": False, "first_name": "Admin"},
                "text": "Reject",
                "reply_to_message": {
                    "message_id": 60,
                    "from": {"id": 777, "is_bot": True},
                    "text": f"<b>Request #{request.id}</b>\n\n<a href='tg://user?id={client_id}'>Test2</a> (ID: {client_id})\n\n<b>Message:</b>\nSuspicious request\n\nReply with 'Approve' or 'Reject' or use the buttons below",
                },
            },
        }

        # Send rejection update
        response = client.post("/webhook/telegram", json=update_json)

        # Verify endpoint returns 200
        assert response.status_code == 200
        assert response.json()["ok"] is True

        # Verify request status updated in database
        db = SessionLocal()
        try:
            updated_request = db.query(AccessRequest).filter(AccessRequest.id == request.id).first()
            assert updated_request is not None
            assert updated_request.status == RequestStatus.REJECTED
            assert updated_request.admin_telegram_id == str(admin_id)
        finally:
            db.close()

    def test_rejection_with_invalid_request(self, client, mock_bot):
        """Test rejection when request doesn't exist (T048).

        Contract: POST /webhook/telegram with "Reject" when request doesn't exist
        → returns 200, admin receives error "Request not found".
        """
        admin_id = 555666777

        # Create update with rejection but no valid request ID
        update_json = {
            "update_id": 201,
            "message": {
                "message_id": 201,
                "date": int(datetime.now(timezone.utc).timestamp()),
                "chat": {"id": admin_id, "type": "private"},
                "from": {"id": admin_id, "is_bot": False, "first_name": "Admin"},
                "text": "Reject",
                "reply_to_message": {
                    "message_id": 199,
                    "from": {"id": 777, "is_bot": True},
                    "text": "<b>Request #99999</b>\n\n<a href='tg://user?id=999999'>Unknown</a> (ID: 999999)\n\n<b>Message:</b>\nTest\n\nReply with 'Approve' or 'Reject' or use the buttons below",
                },
            },
        }

        # Send rejection update
        response = client.post("/webhook/telegram", json=update_json)

        # Verify endpoint returns 200
        assert response.status_code == 200
        assert response.json()["ok"] is True

        # Verify no requests in database
        db = SessionLocal()
        try:
            all_requests = db.query(AccessRequest).all()
            assert len(all_requests) == 0
        finally:
            db.close()
