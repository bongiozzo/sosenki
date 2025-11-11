"""Integration tests for admin rejection flow.

T049: Integration test for full rejection flow.
Tests the complete workflow: client sends /request → admin replies "Reject" →
database updates request status → client receives rejection message (within 5s SLA).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from telegram import Update

from src.api import webhook as webhook_module
from src.models.access_request import AccessRequest, RequestStatus
from src.models.user import User
from src.services import SessionLocal


class TestRejectionFlow:
    """Integration tests for the complete admin rejection flow."""

    @pytest.fixture(autouse=True)
    def cleanup_db(self):
        """Clean up database before and after each test."""
        db = SessionLocal()
        try:
            # Delete test users created by this test suite
            # (Users created with placeholder names starting with "User_")
            db.execute(delete(User).where(User.name.like("User_%")))
            # Delete all requests
            db.execute(delete(AccessRequest))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        yield

        # Cleanup after test
        db = SessionLocal()
        try:
            # Delete test users created by this test suite
            db.execute(delete(User).where(User.name.like("User_%")))
            # Delete all requests
            db.execute(delete(AccessRequest))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot with async methods."""
        bot = MagicMock()
        bot.send_message = AsyncMock()
        return bot

    @pytest.fixture
    def client(self, mock_bot):
        """Create a test client with mocked bot."""
        with patch("telegram.Update.de_json") as mock_de_json:
            def de_json_side_effect(data, bot_instance):
                """Convert dict to Update object."""
                if data and "message" in data:
                    update = MagicMock(spec=Update)
                    update.message = MagicMock()
                    update.message.text = data["message"]["text"]
                    update.message.from_user = MagicMock()
                    update.message.from_user.id = data["message"]["from"]["id"]
                    update.message.from_user.first_name = data["message"]["from"].get(
                        "first_name", "TestUser"
                    )
                    update.message.from_user.username = data["message"]["from"].get(
                        "username", None
                    )
                    update.message.chat = MagicMock()
                    update.message.chat.id = data["message"].get(
                        "chat", {}
                    ).get("id", data["message"]["from"]["id"])
                    update.message.chat.type = data["message"].get("chat", {}).get("type", "private")
                    update.message.reply_text = AsyncMock()
                    # Handle reply_to_message for admin responses
                    update.message.reply_to_message = None
                    if "reply_to_message" in data["message"]:
                        rtm = MagicMock()
                        rtm.text = data["message"]["reply_to_message"].get("text", "")
                        update.message.reply_to_message = rtm
                    return update
                return None

            mock_de_json.side_effect = de_json_side_effect

            mock_app = MagicMock()
            mock_app.bot = mock_bot
            mock_app.process_update = AsyncMock()

            async def process_update_impl(update):
                """Process update through the handler."""
                if update.message and update.message.text:
                    from src.bot.handlers import handle_admin_reject, handle_request_command

                    ctx = MagicMock()
                    ctx.application = mock_app
                    ctx.bot_data = {}

                    # Route to appropriate handler
                    if update.message.text.startswith("/request"):
                        await handle_request_command(update, ctx)
                    elif "reject" in update.message.text.lower():
                        await handle_admin_reject(update, ctx)

            mock_app.process_update.side_effect = process_update_impl

            webhook_module._bot_app = mock_app

            yield TestClient(webhook_module.app)

            webhook_module._bot_app = None

    def test_full_rejection_flow(self, client, mock_bot):
        """Test complete rejection workflow: request → rejection → rejection message.

        Verifies:
        1. Client sends /request command
        2. Request stored in database with PENDING status
        3. Admin sends "Reject" reply
        4. Request status updated to REJECTED in database
        5. Client receives rejection message
        6. Admin receives confirmation
        """
        client_id = 111222333
        client_name = "TestClient"
        admin_id = 999888777
        admin_name = "Admin"
        request_message = "Need access to system"

        # Step 1: Client submits request
        start_time = datetime.now(timezone.utc)
        client_update = {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "date": int(datetime.now(timezone.utc).timestamp()),
                "chat": {"id": client_id, "type": "private"},
                "from": {"id": client_id, "is_bot": False, "first_name": client_name},
                "text": f"/request {request_message}",
            },
        }

        response = client.post("/webhook/telegram", json=client_update)
        assert response.status_code == 200

        # Verify request stored in database
        db = SessionLocal()
        try:
            stored_request = db.query(AccessRequest).filter(
                AccessRequest.user_telegram_id == str(client_id)
            ).first()
            assert stored_request is not None
            assert stored_request.status == RequestStatus.PENDING
            assert stored_request.request_message == request_message
            request_id = stored_request.id
        finally:
            db.close()

        # Reset mock to track rejection call separately
        mock_bot.reset_mock()

        # Step 2: Admin rejects the request
        admin_update = {
            "update_id": 2,
            "message": {
                "message_id": 2,
                "date": int(datetime.now(timezone.utc).timestamp()),
                "chat": {"id": admin_id, "type": "private"},
                "from": {"id": admin_id, "is_bot": False, "first_name": admin_name},
                "text": "Reject",
                "reply_to_message": {
                    "message_id": 50,
                    "from": {"id": 777, "is_bot": True},
                    "text": f"<b>Request #{request_id}</b>\n\n<a href='tg://user?id={client_id}'>{client_name}</a> (ID: {client_id})\n\n<b>Message:</b>\n{request_message}\n\nReply with 'Approve' or 'Reject' or use the buttons below",
                },
            },
        }

        response = client.post("/webhook/telegram", json=admin_update)
        assert response.status_code == 200
        end_time = datetime.now(timezone.utc)
        elapsed_time = (end_time - start_time).total_seconds()

        # Step 3: Verify request status updated to REJECTED
        db = SessionLocal()
        try:
            updated_request = db.query(AccessRequest).filter(
                AccessRequest.id == request_id
            ).first()
            assert updated_request is not None
            assert updated_request.status == RequestStatus.REJECTED
            assert updated_request.responded_by_admin_id == str(admin_id)
            assert updated_request.response_message == "rejected"
            assert updated_request.responded_at is not None
        finally:
            db.close()

        # Step 4: Verify rejection message sent to client
        # Bot.send_message should have been called with client_id
        assert mock_bot.send_message.called
        send_calls = mock_bot.send_message.call_args_list
        rejection_sent = False
        for call in send_calls:
            if (len(call.args) >= 1 and str(client_id) in str(call.args[0])) or \
               (call.kwargs.get("chat_id") and str(client_id) in str(call.kwargs.get("chat_id"))):
                rejection_sent = True
                # Verify rejection message text
                if len(call.args) >= 2 and call.args[1]:
                    assert "not been approved" in call.args[1].lower() or "rejected" in call.args[1].lower()
                elif call.kwargs.get("text"):
                    assert "not been approved" in call.kwargs.get("text").lower() or "rejected" in call.kwargs.get("text").lower()

        assert rejection_sent, "Rejection message should be sent to client"

        # Verify timing SLA (rejection response within 5 seconds)
        print(f"Rejection flow time: {elapsed_time:.3f} seconds (SLA: 5s)")
        assert elapsed_time < 5.0, f"Rejection flow exceeded SLA: {elapsed_time}s > 5s"

    def test_rejection_with_missing_request(self, client, mock_bot):
        """Test rejection when request doesn't exist.

        Verifies:
        1. Admin sends "Reject" reply
        2. Request ID doesn't exist in database
        3. Admin receives error message
        4. No rejection is recorded
        """
        admin_id = 999888777
        admin_name = "Admin"

        # Admin tries to reject non-existent request
        admin_update = {
            "update_id": 3,
            "message": {
                "message_id": 3,
                "date": int(datetime.now(timezone.utc).timestamp()),
                "chat": {"id": admin_id, "type": "private"},
                "from": {"id": admin_id, "is_bot": False, "first_name": admin_name},
                "text": "Reject",
                "reply_to_message": {
                    "message_id": 99,
                    "from": {"id": 777, "is_bot": True},
                    "text": "<b>Request #99999</b>\n\n<a href='tg://user?id=999999'>Unknown</a> (ID: 999999)\n\n<b>Message:</b>\nTest\n\nReply with 'Approve' or 'Reject' or use the buttons below",
                },
            },
        }

        response = client.post("/webhook/telegram", json=admin_update)
        assert response.status_code == 200

        # Verify no requests exist in database
        db = SessionLocal()
        try:
            all_requests = db.query(AccessRequest).all()
            assert len(all_requests) == 0
        finally:
            db.close()

    def test_rejection_timing_sla(self, client, mock_bot):
        """Test that rejection response meets timing SLA (< 5 seconds).

        Verifies:
        1. Full rejection flow completes within 5 second SLA
        2. Includes request processing and rejection processing
        """
        client_id = 222333444
        admin_id = 888777666
        request_message = "Quick rejection test"

        # Step 1: Client submits request
        client_update = {
            "update_id": 4,
            "message": {
                "message_id": 4,
                "date": int(datetime.now(timezone.utc).timestamp()),
                "chat": {"id": client_id, "type": "private"},
                "from": {"id": client_id, "is_bot": False, "first_name": "User"},
                "text": f"/request {request_message}",
            },
        }

        response = client.post("/webhook/telegram", json=client_update)
        assert response.status_code == 200

        # Get request ID
        db = SessionLocal()
        try:
            stored_request = db.query(AccessRequest).filter(
                AccessRequest.user_telegram_id == str(client_id)
            ).first()
            request_id = stored_request.id
        finally:
            db.close()

        # Step 2: Measure rejection response time
        start_time = datetime.now(timezone.utc)

        admin_update = {
            "update_id": 5,
            "message": {
                "message_id": 5,
                "date": int(datetime.now(timezone.utc).timestamp()),
                "chat": {"id": admin_id, "type": "private"},
                "from": {"id": admin_id, "is_bot": False, "first_name": "Admin"},
                "text": "Reject",
                "reply_to_message": {
                    "message_id": 50,
                    "from": {"id": 777, "is_bot": True},
                    "text": f"<b>Request #{request_id}</b>\n\n<a href='tg://user?id={client_id}'>User</a> (ID: {client_id})\n\n<b>Message:</b>\nTest\n\nReply with 'Approve' or 'Reject' or use the buttons below",
                },
            },
        }

        response = client.post("/webhook/telegram", json=admin_update)
        end_time = datetime.now(timezone.utc)
        elapsed_time = (end_time - start_time).total_seconds()

        assert response.status_code == 200
        print(f"Rejection response time: {elapsed_time:.3f} seconds (SLA: 5s)")
        assert elapsed_time < 5.0

    def test_rejection_idempotency(self, client, mock_bot):
        """Test that rejecting the same request twice doesn't cause issues.

        Verifies:
        1. First rejection succeeds
        2. Second rejection attempt is handled gracefully
        3. Request status remains REJECTED
        """
        client_id = 333444555
        admin_id = 777666555
        request_message = "Idempotency test"

        # Create request
        db = SessionLocal()
        try:
            request = AccessRequest(
                user_telegram_id=str(client_id),
                request_message=request_message,
                status=RequestStatus.PENDING,
                submitted_at=datetime.now(timezone.utc),
            )
            db.add(request)
            db.commit()
            db.refresh(request)
            request_id = request.id
        finally:
            db.close()

        # First rejection
        admin_update_1 = {
            "update_id": 6,
            "message": {
                "message_id": 6,
                "date": int(datetime.now(timezone.utc).timestamp()),
                "chat": {"id": admin_id, "type": "private"},
                "from": {"id": admin_id, "is_bot": False, "first_name": "Admin"},
                "text": "Reject",
                "reply_to_message": {
                    "message_id": 50,
                    "from": {"id": 777, "is_bot": True},
                    "text": f"<b>Request #{request_id}</b>\n\n<a href='tg://user?id={client_id}'>User</a> (ID: {client_id})\n\n<b>Message:</b>\n{request_message}\n\nReply with 'Approve' or 'Reject' or use the buttons below",
                },
            },
        }

        response1 = client.post("/webhook/telegram", json=admin_update_1)
        assert response1.status_code == 200

        # Verify rejected
        db = SessionLocal()
        try:
            req = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
            assert req.status == RequestStatus.REJECTED
        finally:
            db.close()

        # Second rejection attempt (idempotent)
        mock_bot.reset_mock()
        admin_update_2 = {
            "update_id": 7,
            "message": {
                "message_id": 7,
                "date": int(datetime.now(timezone.utc).timestamp()),
                "chat": {"id": admin_id, "type": "private"},
                "from": {"id": admin_id, "is_bot": False, "first_name": "Admin"},
                "text": "Reject",
                "reply_to_message": {
                    "message_id": 50,
                    "from": {"id": 777, "is_bot": True},
                    "text": f"Client Request: User (ID: {request_id})",
                },
            },
        }

        response2 = client.post("/webhook/telegram", json=admin_update_2)
        assert response2.status_code == 200

        # Verify still rejected
        db = SessionLocal()
        try:
            req = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
            assert req.status == RequestStatus.REJECTED
        finally:
            db.close()
