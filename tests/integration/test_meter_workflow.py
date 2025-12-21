"""Integration tests for /meter electricity reading workflow.

Tests the complete workflow:
- Admin starts /meter command
- Selects property
- Chooses action (new/edit/delete)
- Enters date and value
- System validates and saves reading
- Audit log is created
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import delete, select

from src.models.audit_log import AuditLog
from src.models.electricity_reading import ElectricityReading
from src.models.property import Property
from src.models.user import User
from src.services import SessionLocal


class TestMeterWorkflow:
    """Integration tests for the complete /meter workflow."""

    @pytest.fixture(autouse=True)
    def cleanup_db(self):
        """Clean up and setup database before and after each test."""
        db = SessionLocal()
        try:
            db.execute(delete(AuditLog))
            db.execute(delete(ElectricityReading))
            db.execute(delete(Property))
            db.execute(delete(User))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        # Setup: Create admin user and properties
        db = SessionLocal()
        try:
            # Create admin user
            admin = User(
                telegram_id=999888777,
                name="Test Admin",
                is_active=True,
                is_administrator=True,
            )
            db.add(admin)
            db.flush()

            # Create property owner
            owner = User(
                telegram_id=111222333,
                name="Property Owner",
                is_active=True,
                is_owner=True,
            )
            db.add(owner)
            db.flush()

            # Create properties
            property1 = Property(
                owner_id=owner.id,
                property_name="Test Property 1",
                share_weight=Decimal("0.5"),
                is_active=True,
                is_ready=True,
            )
            property2 = Property(
                owner_id=owner.id,
                property_name="Test Property 2",
                share_weight=Decimal("0.3"),
                is_active=True,
                is_ready=True,
            )
            db.add_all([property1, property2])
            db.commit()

            # Store IDs for tests
            self.admin_id = admin.id
            self.owner_id = owner.id
            self.property1_id = property1.id
            self.property2_id = property2.id

        except Exception:
            db.rollback()
        finally:
            db.close()

        yield

        # Cleanup after test
        db = SessionLocal()
        try:
            db.execute(delete(AuditLog))
            db.execute(delete(ElectricityReading))
            db.execute(delete(Property))
            db.execute(delete(User))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_full_meter_new_reading_workflow(self):
        """Test complete workflow: /meter → select property → new reading → enter date/value → confirm."""
        from src.bot.handlers.admin_meter import (
            handle_action_selection as handle_meter_action_selection,
        )
        from src.bot.handlers.admin_meter import (
            handle_date_input,
            handle_final_confirmation,
            handle_meter_command,
            handle_property_selection,
            handle_value_input,
        )

        # Mock Update and Context objects
        update = MagicMock()
        context = MagicMock()
        context.user_data = {}

        # Step 1: Admin sends /meter command
        update.message = MagicMock()
        update.message.from_user = MagicMock()
        update.message.from_user.id = 999888777
        update.message.reply_text = AsyncMock()
        update.callback_query = None  # No callback yet, only message

        state = await handle_meter_command(update, context)

        # Verify property selection prompt was sent
        assert state == 20  # States.SELECT_PROPERTY
        assert update.message.reply_text.called
        assert context.user_data["meter_admin_id"] == 999888777

        # Step 2: Admin selects property
        update.callback_query = MagicMock()
        update.callback_query.data = f"meter_property_{self.property1_id}"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.message = MagicMock()
        update.callback_query.message.reply_text = AsyncMock()
        update.message = None

        state = await handle_property_selection(update, context)

        # Verify action selection prompt
        assert state == 21  # States.SELECT_ACTION
        assert context.user_data["meter_property_id"] == self.property1_id
        assert context.user_data["meter_property_name"] == "Test Property 1"

        # Step 3: Admin selects "new reading" action
        update.callback_query.data = "meter_action_new"

        state = await handle_meter_action_selection(update, context)

        # Verify date input prompt
        assert state == 23  # States.ENTER_DATE
        assert context.user_data["meter_action"] == "new"

        # Step 4: Admin enters date
        update.message = MagicMock()
        update.message.text = "15.12.2025"
        update.message.reply_text = AsyncMock()
        update.callback_query = None

        state = await handle_date_input(update, context)

        # Verify value input prompt
        assert state == 24  # States.ENTER_VALUE
        assert context.user_data["meter_date"] == date(2025, 12, 15)

        # Step 5: Admin enters value
        update.message.text = "1500.5"

        state = await handle_value_input(update, context)

        # Verify confirmation prompt was shown
        assert state == 25  # States.CONFIRM
        assert context.user_data["meter_value"] == Decimal("1500.5")
        assert update.message.reply_text.called

        # Step 6: Admin confirms
        update.callback_query = MagicMock()
        update.callback_query.data = "meter_confirm_save"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.message = None

        state = await handle_final_confirmation(update, context)

        # Verify workflow loops back to property selection
        assert state == 20  # States.SELECT_PROPERTY
        assert update.callback_query.edit_message_text.called

        # Verify database state
        db = SessionLocal()
        try:
            # Check reading was created
            stmt = select(ElectricityReading).where(
                ElectricityReading.property_id == self.property1_id
            )
            result = db.execute(stmt)
            reading = result.scalar_one_or_none()

            assert reading is not None
            assert reading.reading_value == Decimal("1500.5")
            assert reading.reading_date == date(2025, 12, 15)
            assert reading.property_id == self.property1_id

            # Check audit log was created
            stmt = select(AuditLog).where(
                AuditLog.entity_type == "ElectricityReading",
                AuditLog.action == "create",
            )
            result = db.execute(stmt)
            audit = result.scalar_one_or_none()

            assert audit is not None
            assert audit.actor_id == 999888777  # telegram_id used as actor_id
            assert "reading_value" in audit.changes

        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_meter_edit_reading_workflow(self):
        """Test workflow: /meter → select property → edit reading → update date/value → confirm."""
        from src.bot.handlers.admin_meter import (
            handle_action_selection as handle_meter_action_selection,
        )
        from src.bot.handlers.admin_meter import (
            handle_date_input,
            handle_final_confirmation,
            handle_meter_command,
            handle_property_selection,
            handle_value_input,
        )

        # Setup: Create initial reading
        db = SessionLocal()
        try:
            initial_reading = ElectricityReading(
                property_id=self.property1_id,
                reading_date=date(2025, 12, 1),
                reading_value=Decimal("1000.0"),
            )
            db.add(initial_reading)
            db.commit()
            reading_id = initial_reading.id
        finally:
            db.close()

        # Mock Update and Context
        update = MagicMock()
        context = MagicMock()
        context.user_data = {}

        # Step 1: Start /meter command
        update.message = MagicMock()
        update.message.from_user = MagicMock()
        update.message.from_user.id = 999888777
        update.message.reply_text = AsyncMock()
        update.callback_query = None  # No callback yet, only message

        await handle_meter_command(update, context)

        # Step 2: Select property
        update.callback_query = AsyncMock()
        update.callback_query.data = f"meter_property_{self.property1_id}"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.message = MagicMock()
        update.callback_query.message.reply_text = AsyncMock()
        update.message = None

        await handle_property_selection(update, context)

        # Step 3: Select "edit" action
        update.callback_query.data = "meter_action_edit"

        state = await handle_meter_action_selection(update, context)

        # Verify edit action was set
        assert state == 23  # States.ENTER_DATE
        assert context.user_data["meter_action"] == "edit"
        assert context.user_data["meter_reading_id"] == reading_id

        # Step 4: Enter new date
        update.message = MagicMock()
        update.message.text = "15.12.2025"
        update.message.reply_text = AsyncMock()
        update.callback_query = None

        await handle_date_input(update, context)

        # Step 5: Enter new value (must be greater than previous)
        update.message.text = "1500.0"

        state = await handle_value_input(update, context)

        # Verify confirmation prompt was shown
        assert state == 25  # States.CONFIRM
        assert context.user_data["meter_value"] == Decimal("1500.0")

        # Step 6: Admin confirms
        update.callback_query = AsyncMock()
        update.callback_query.data = "meter_confirm_save"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.message = MagicMock()
        update.callback_query.message.reply_text = AsyncMock()
        update.message = None

        state = await handle_final_confirmation(update, context)

        # Verify workflow loops back to property selection
        assert state == 20  # States.SELECT_PROPERTY

        # Verify database was updated
        db = SessionLocal()
        try:
            stmt = select(ElectricityReading).where(ElectricityReading.id == reading_id)
            result = db.execute(stmt)
            updated_reading = result.scalar_one_or_none()

            assert updated_reading is not None
            assert updated_reading.reading_value == Decimal("1500.0")
            assert updated_reading.reading_date == date(2025, 12, 15)

            # Check audit log for update
            stmt = select(AuditLog).where(
                AuditLog.entity_type == "ElectricityReading",
                AuditLog.action == "update",
                AuditLog.entity_id == reading_id,
            )
            result = db.execute(stmt)
            audit = result.scalar_one_or_none()

            assert audit is not None
            assert audit.actor_id == 999888777  # telegram_id used as actor_id

        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_meter_delete_reading_workflow(self):
        """Test workflow: /meter → select property → delete reading → confirm deletion."""
        from src.bot.handlers.admin_meter import (
            handle_action_selection as handle_meter_action_selection,
        )
        from src.bot.handlers.admin_meter import (
            handle_delete_confirmation,
            handle_meter_command,
            handle_property_selection,
        )

        # Setup: Create initial reading
        db = SessionLocal()
        try:
            initial_reading = ElectricityReading(
                property_id=self.property1_id,
                reading_date=date(2025, 12, 1),
                reading_value=Decimal("1000.0"),
            )
            db.add(initial_reading)
            db.commit()
            reading_id = initial_reading.id
        finally:
            db.close()

        # Mock Update and Context
        update = MagicMock()
        context = MagicMock()
        context.user_data = {}

        # Step 1: Start /meter command
        update.message = MagicMock()
        update.message.from_user = MagicMock()
        update.message.from_user.id = 999888777
        update.message.reply_text = AsyncMock()
        update.callback_query = None  # No callback yet, only message

        await handle_meter_command(update, context)

        # Step 2: Select property
        update.callback_query = AsyncMock()
        update.callback_query.data = f"meter_property_{self.property1_id}"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.message = MagicMock()
        update.callback_query.message.reply_text = AsyncMock()
        update.message = None

        await handle_property_selection(update, context)

        # Step 3: Select "delete" action
        update.callback_query.data = "meter_action_delete"

        state = await handle_meter_action_selection(update, context)

        # Verify delete confirmation prompt
        assert state == 22  # States.CONFIRM_DELETE
        assert context.user_data["meter_action"] == "delete"
        assert context.user_data["meter_reading_id"] == reading_id

        # Step 4: Confirm deletion
        update.callback_query.data = "meter_confirm_delete"

        state = await handle_delete_confirmation(update, context)

        # Verify workflow loops back to property selection
        assert state == 20  # States.SELECT_PROPERTY

        # Verify reading was deleted
        db = SessionLocal()
        try:
            stmt = select(ElectricityReading).where(ElectricityReading.id == reading_id)
            result = db.execute(stmt)
            deleted_reading = result.scalar_one_or_none()

            assert deleted_reading is None  # Reading should be deleted

            # Check audit log for deletion
            stmt = select(AuditLog).where(
                AuditLog.entity_type == "ElectricityReading",
                AuditLog.action == "delete",
            )
            result = db.execute(stmt)
            audit = result.scalar_one_or_none()

            assert audit is not None
            assert audit.actor_id == 999888777  # telegram_id used as actor_id

        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_meter_validation_value_must_be_positive(self):
        """Test that negative or zero values are rejected."""
        from src.bot.handlers.admin_meter import (
            handle_action_selection as handle_meter_action_selection,
        )
        from src.bot.handlers.admin_meter import (
            handle_date_input,
            handle_meter_command,
            handle_property_selection,
            handle_value_input,
        )

        update = MagicMock()
        context = MagicMock()
        context.user_data = {}

        # Navigate to value input
        update.message = MagicMock()
        update.message.from_user = MagicMock()
        update.message.from_user.id = 999888777
        update.message.reply_text = AsyncMock()

        await handle_meter_command(update, context)

        update.callback_query = AsyncMock()
        update.callback_query.data = f"meter_property_{self.property1_id}"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.message = MagicMock()
        update.callback_query.message.reply_text = AsyncMock()
        update.message = None

        await handle_property_selection(update, context)

        update.callback_query.data = "meter_action_new"
        await handle_meter_action_selection(update, context)

        update.message = MagicMock()
        update.message.text = "15.12.2025"
        update.message.reply_text = AsyncMock()
        update.callback_query = None

        await handle_date_input(update, context)

        # Try to enter negative value
        update.message.text = "-100"

        state = await handle_value_input(update, context)

        # Should stay in value input state
        assert state == 24  # States.ENTER_VALUE
        # Verify error message was sent
        assert update.message.reply_text.called

    @pytest.mark.asyncio
    async def test_meter_validation_value_must_increase(self):
        """Test that new reading must be greater than previous reading."""
        from src.bot.handlers.admin_meter import (
            handle_action_selection as handle_meter_action_selection,
        )
        from src.bot.handlers.admin_meter import (
            handle_date_input,
            handle_final_confirmation,
            handle_meter_command,
            handle_property_selection,
            handle_value_input,
        )

        # Setup: Create initial reading
        db = SessionLocal()
        try:
            initial_reading = ElectricityReading(
                property_id=self.property1_id,
                reading_date=date(2025, 12, 1),
                reading_value=Decimal("1000.0"),
            )
            db.add(initial_reading)
            db.commit()
        finally:
            db.close()

        update = MagicMock()
        context = MagicMock()
        context.user_data = {}

        # Navigate to value input
        update.message = MagicMock()
        update.message.from_user = MagicMock()
        update.message.from_user.id = 999888777
        update.message.reply_text = AsyncMock()
        update.callback_query = None  # No callback yet, only message

        await handle_meter_command(update, context)

        # Step 2: Select property
        update.callback_query = AsyncMock()
        update.callback_query.data = f"meter_property_{self.property1_id}"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.message = None

        await handle_property_selection(update, context)

        # Step 3: Select "new" action
        update.callback_query.data = "meter_action_new"
        await handle_meter_action_selection(update, context)

        # Step 4: Enter date
        update.message = MagicMock()
        update.message.text = "15.12.2025"
        update.message.reply_text = AsyncMock()
        update.callback_query = None

        await handle_date_input(update, context)

        # Try to enter value less than previous (1000.0)
        update.message.text = "900.0"

        state = await handle_value_input(update, context)

        # Validation now happens at value input (early validation)
        # Should return to ENTER_VALUE state, not proceed to CONFIRM
        assert state == 24  # States.ENTER_VALUE
        # Verify error message was shown
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args[0][0]
        assert "900.0" in call_args  # Error message should mention the invalid value
        assert "1000.0" in call_args  # Should mention the previous value

        # Verify no new reading was created
        db = SessionLocal()
        try:
            stmt = select(ElectricityReading).where(
                ElectricityReading.property_id == self.property1_id
            )
            result = db.execute(stmt)
            readings = result.scalars().all()

            # Should only have the initial reading
            assert len(readings) == 1
            assert readings[0].reading_value == Decimal("1000.0")

        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_meter_cancel_workflow(self):
        """Test that cancel button properly terminates workflow."""
        from src.bot.handlers.admin_meter import handle_meter_cancel, handle_meter_command

        update = MagicMock()
        context = MagicMock()
        context.user_data = {}

        # Start workflow
        update.message = MagicMock()
        update.message.from_user = MagicMock()
        update.message.from_user.id = 999888777
        update.message.reply_text = AsyncMock()
        update.callback_query = None  # No callback yet, only message

        await handle_meter_command(update, context)

        # Verify context was set
        assert "meter_admin_id" in context.user_data

        # Cancel workflow
        state = await handle_meter_cancel(update, context)

        # Verify workflow ended
        assert state == -1  # States.END

        # Verify context was cleared
        assert "meter_admin_id" not in context.user_data
        assert "meter_property_id" not in context.user_data

    @pytest.mark.asyncio
    async def test_meter_unauthorized_access(self):
        """Test that non-admin users cannot access /meter command."""
        from src.bot.handlers.admin_meter import handle_meter_command

        # Create non-admin user
        db = SessionLocal()
        try:
            regular_user = User(
                telegram_id=555444333,
                name="Regular User",
                is_active=True,
                is_administrator=False,  # Not admin
            )
            db.add(regular_user)
            db.commit()
        finally:
            db.close()

        update = MagicMock()
        context = MagicMock()
        context.user_data = {}

        update.message = MagicMock()
        update.message.from_user = MagicMock()
        update.message.from_user.id = 555444333  # Non-admin telegram_id
        update.message.reply_text = AsyncMock()

        state = await handle_meter_command(update, context)

        # Verify workflow ended without granting access
        assert state == -1  # States.END
        # Verify error message was sent
        assert update.message.reply_text.called
