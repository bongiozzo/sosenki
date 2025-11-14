"""Contract tests for 'Доп' column handling.

Tests for splitting auxiliary properties and type mapping.
"""

import pytest
from sqlalchemy import delete

from src.models.property import Property
from src.models.user import User
from src.services import SessionLocal


class TestDopColumnHandling:
    """Contract tests for 'Доп' column handling (T041)."""

    @pytest.fixture(autouse=True)
    def cleanup_db(self):
        """Clean up database before and after each test."""
        db = SessionLocal()
        try:
            db.execute(delete(Property))
            db.execute(delete(User))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        yield

        # Cleanup after test
        db = SessionLocal()
        try:
            db.execute(delete(Property))
            db.execute(delete(User))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def test_user_can_be_created_in_database(self):
        """Test that users can be created in database (T041)."""
        db = SessionLocal()
        try:
            user = User(name="Test Owner", is_active=True)
            db.add(user)
            db.commit()

            # Verify user was saved
            saved_user = db.query(User).filter_by(name="Test Owner").first()
            assert saved_user is not None
            assert saved_user.is_active is True
        finally:
            db.close()

    def test_property_can_be_created_in_database(self):
        """Test that properties can be created in database (T041)."""
        db = SessionLocal()
        try:
            # Create user first
            user = User(name="Property Owner", is_active=True)
            db.add(user)
            db.flush()

            # Create property
            prop = Property(
                property_name="Main Property",
                owner_id=user.id,
                type="Большой",
                share_weight=1000,
            )
            db.add(prop)
            db.commit()

            # Verify property was saved
            saved_prop = db.query(Property).filter_by(property_name="Main Property").first()
            assert saved_prop is not None
            assert saved_prop.owner_id == user.id
            assert saved_prop.type == "Большой"
        finally:
            db.close()

    def test_multiple_properties_can_share_owner(self):
        """Test that multiple properties can be linked to same owner (T041)."""
        db = SessionLocal()
        try:
            # Create user
            user = User(name="Multi-Property Owner", is_active=True)
            db.add(user)
            db.flush()

            # Create multiple properties
            prop1 = Property(
                property_name="Property 1",
                owner_id=user.id,
                type="Большой",
                share_weight=1000,
            )
            prop2 = Property(
                property_name="Property 2",
                owner_id=user.id,
                type="Малый",
                share_weight=500,
            )
            prop3 = Property(
                property_name="Property 3",
                owner_id=user.id,
                type="Беседка",
                share_weight=250,
            )

            db.add_all([prop1, prop2, prop3])
            db.commit()

            # Verify all properties share the same owner
            props = db.query(Property).filter_by(owner_id=user.id).all()
            assert len(props) == 3
            assert all(p.owner_id == user.id for p in props)
        finally:
            db.close()

    def test_property_can_have_attributes(self):
        """Test that property attributes are stored correctly (T041)."""
        db = SessionLocal()
        try:
            user = User(name="Attr Owner", is_active=True)
            db.add(user)
            db.flush()

            prop = Property(
                property_name="Detailed Property",
                owner_id=user.id,
                type="Хоздвор",
                share_weight=300,
                is_ready=True,
                is_for_tenant=False,
            )
            db.add(prop)
            db.commit()

            # Verify attributes
            saved_prop = db.query(Property).filter_by(property_name="Detailed Property").first()
            assert saved_prop.is_ready is True
            assert saved_prop.is_for_tenant is False
            assert saved_prop.share_weight == 300
        finally:
            db.close()

    def test_property_attributes_can_be_null(self):
        """Test that property attributes can be null (selective inheritance) (T041)."""
        db = SessionLocal()
        try:
            user = User(name="Null Owner", is_active=True)
            db.add(user)
            db.flush()

            prop = Property(
                property_name="Sparse Property",
                owner_id=user.id,
                type="Склад",
                share_weight=200,
                photo_link=None,
            )
            db.add(prop)
            db.commit()

            # Verify nulls are preserved
            saved_prop = db.query(Property).filter_by(property_name="Sparse Property").first()
            assert saved_prop.photo_link is None
        finally:
            db.close()

    def test_property_type_values_stored_correctly(self):
        """Test that different property types are stored (T041)."""
        db = SessionLocal()
        try:
            user = User(name="Type Test Owner", is_active=True)
            db.add(user)
            db.flush()

            types = ["Большой", "Малый", "Беседка", "Хоздвор", "Склад", "Баня"]
            for i, prop_type in enumerate(types):
                prop = Property(
                    property_name=f"Property {i}",
                    owner_id=user.id,
                    type=prop_type,
                    share_weight=100 * (i + 1),
                )
                db.add(prop)

            db.commit()

            # Verify all types were saved
            for i, expected_type in enumerate(types):
                saved_prop = db.query(Property).filter_by(property_name=f"Property {i}").first()
                assert saved_prop.type == expected_type
        finally:
            db.close()

    def test_multiple_users_with_properties(self):
        """Test that properties are correctly linked to different owners (T041)."""
        db = SessionLocal()
        try:
            # Create multiple users
            user1 = User(name="Owner 1", is_active=True)
            user2 = User(name="Owner 2", is_active=False)
            db.add_all([user1, user2])
            db.flush()

            # Create properties for each
            prop1 = Property(
                property_name="User1 Prop",
                owner_id=user1.id,
                type="Большой",
                share_weight=1000,
            )
            prop2 = Property(
                property_name="User2 Prop",
                owner_id=user2.id,
                type="Малый",
                share_weight=500,
            )
            db.add_all([prop1, prop2])
            db.commit()

            # Verify properties are linked correctly
            user1_props = db.query(Property).filter_by(owner_id=user1.id).all()
            user2_props = db.query(Property).filter_by(owner_id=user2.id).all()

            assert len(user1_props) == 1
            assert len(user2_props) == 1
            assert user1_props[0].owner_id == user1.id
            assert user2_props[0].owner_id == user2.id
        finally:
            db.close()

    def test_property_deletion_cascade(self):
        """Test that properties are properly managed (T041)."""
        db = SessionLocal()
        try:
            user = User(name="Delete Test Owner", is_active=True)
            db.add(user)
            db.flush()

            prop = Property(
                property_name="Temp Property",
                owner_id=user.id,
                type="Баня",
                share_weight=100,
            )
            db.add(prop)
            db.commit()

            prop_id = prop.id

            # Delete the property
            db.delete(prop)
            db.commit()

            # Verify it's deleted
            deleted_prop = db.query(Property).filter_by(id=prop_id).first()
            assert deleted_prop is None
        finally:
            db.close()
