"""Unit tests for Property model."""

from decimal import Decimal
from sqlalchemy import delete

from src.models import User, Property
from src.services import SessionLocal


class TestPropertyModel:
    """Unit tests for Property ORM model."""

    def setup_method(self):
        """Clean up database before each test."""
        db = SessionLocal()
        try:
            db.execute(delete(Property))
            db.execute(delete(User))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def teardown_method(self):
        """Clean up database after each test."""
        db = SessionLocal()
        try:
            db.execute(delete(Property))
            db.execute(delete(User))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def test_property_creation(self):
        """T023a: Test Property model creation with required fields."""
        db = SessionLocal()
        try:
            owner = User(
                telegram_id="test_owner_123",
                name="John Owner",
                is_owner=True,
                is_active=True,
            )
            db.add(owner)
            db.commit()
            db.refresh(owner)

            prop = Property(
                owner_id=owner.id,
                property_name="27",
                type="Большой",
                share_weight=Decimal("2.5"),
                is_active=True,
            )
            db.add(prop)
            db.commit()
            db.refresh(prop)

            assert prop.id is not None
            assert prop.property_name == "27"
            assert prop.type == "Большой"
            assert prop.share_weight == Decimal("2.5")
            assert prop.is_active is True
        finally:
            db.close()

    def test_property_relationship_to_owner(self):
        """T023b: Test Property.owner relationship (FK to User)."""
        db = SessionLocal()
        try:
            owner = User(
                telegram_id="test_owner_234",
                name="Jane Owner",
                is_owner=True,
                is_active=True,
            )
            db.add(owner)
            db.commit()
            db.refresh(owner)

            prop = Property(
                owner_id=owner.id,
                property_name="34",
                type="Малый",
                share_weight=Decimal("1.5"),
                is_active=True,
            )
            db.add(prop)
            db.commit()
            db.refresh(prop)

            # Refresh to clear session cache
            db.expire_all()

            property_from_db = db.query(Property).filter_by(id=prop.id).first()
            assert property_from_db is not None
            assert property_from_db.owner_id == owner.id
            assert property_from_db.owner.telegram_id == "test_owner_234"
        finally:
            db.close()

    def test_user_relationship_to_properties(self):
        """T023c: Test User.properties reverse relationship."""
        db = SessionLocal()
        try:
            owner = User(
                telegram_id="test_owner_345",
                name="Bob Owner",
                is_owner=True,
                is_active=True,
            )
            db.add(owner)
            db.commit()
            db.refresh(owner)

            prop = Property(
                owner_id=owner.id,
                property_name="45",
                type="Средний",
                share_weight=Decimal("2.0"),
                is_active=True,
            )
            db.add(prop)
            db.commit()

            db.expire_all()

            owner_from_db = db.query(User).filter_by(id=owner.id).first()
            assert owner_from_db is not None
            assert len(owner_from_db.properties) == 1
            assert owner_from_db.properties[0].property_name == "45"
        finally:
            db.close()

    def test_property_multiple_properties_per_owner(self):
        """T024a: Test that one owner can have multiple properties."""
        db = SessionLocal()
        try:
            owner = User(
                telegram_id="test_owner_456",
                name="Alice Owner",
                is_owner=True,
                is_active=True,
            )
            db.add(owner)
            db.commit()
            db.refresh(owner)

            prop1 = Property(
                owner_id=owner.id,
                property_name="1",
                type="Малый",
                share_weight=Decimal("1.0"),
                is_active=True,
            )
            prop2 = Property(
                owner_id=owner.id,
                property_name="34а",
                type="Охрана",
                share_weight=Decimal("0.5"),
                is_active=True,
            )
            db.add_all([prop1, prop2])
            db.commit()

            db.expire_all()

            owner_from_db = db.query(User).filter_by(id=owner.id).first()
            assert len(owner_from_db.properties) == 2
            property_names = {p.property_name for p in owner_from_db.properties}
            assert property_names == {"1", "34а"}
        finally:
            db.close()

    def test_property_is_active_field(self):
        """T024b: Test is_active field for property status tracking."""
        db = SessionLocal()
        try:
            owner = User(
                telegram_id="test_owner_567",
                name="Charlie Owner",
                is_owner=True,
                is_active=True,
            )
            db.add(owner)
            db.commit()
            db.refresh(owner)

            active_prop = Property(
                owner_id=owner.id,
                property_name="active",
                type="Большой",
                share_weight=Decimal("1.0"),
                is_active=True,
            )
            inactive_prop = Property(
                owner_id=owner.id,
                property_name="inactive",
                type="Малый",
                share_weight=Decimal("1.0"),
                is_active=False,
            )
            db.add_all([active_prop, inactive_prop])
            db.commit()

            active_props = db.query(Property).filter_by(is_active=True).all()
            inactive_props = db.query(Property).filter_by(is_active=False).all()

            assert len(active_props) >= 1
            assert len(inactive_props) >= 1
        finally:
            db.close()

    def test_property_repr(self):
        """T024c: Test Property __repr__ method."""
        db = SessionLocal()
        try:
            owner = User(
                telegram_id="test_owner_678",
                name="David Owner",
                is_owner=True,
                is_active=True,
            )
            db.add(owner)
            db.commit()
            db.refresh(owner)

            prop = Property(
                owner_id=owner.id,
                property_name="27",
                type="Большой",
                share_weight=Decimal("2.5"),
                is_active=True,
            )
            db.add(prop)
            db.commit()
            db.refresh(prop)

            repr_str = repr(prop)
            assert "Property" in repr_str
            assert "27" in repr_str
        finally:
            db.close()

    def test_property_share_weight_precision(self):
        """T024d: Test share_weight decimal precision (Numeric(10, 2))."""
        db = SessionLocal()
        try:
            owner = User(
                telegram_id="test_owner_789",
                name="Eve Owner",
                is_owner=True,
                is_active=True,
            )
            db.add(owner)
            db.commit()
            db.refresh(owner)

            prop = Property(
                owner_id=owner.id,
                property_name="precision_test",
                type="Большой",
                share_weight=Decimal("3.75"),
                is_active=True,
            )
            db.add(prop)
            db.commit()

            db.expire_all()

            prop_from_db = db.query(Property).filter_by(property_name="precision_test").first()
            assert prop_from_db.share_weight == Decimal("3.75")
        finally:
            db.close()

    def test_property_timestamps_inherited(self):
        """T024e: Test that Property inherits created_at and updated_at from BaseModel."""
        db = SessionLocal()
        try:
            owner = User(
                telegram_id="test_owner_890",
                name="Frank Owner",
                is_owner=True,
                is_active=True,
            )
            db.add(owner)
            db.commit()
            db.refresh(owner)

            prop = Property(
                owner_id=owner.id,
                property_name="timestamps",
                type="Большой",
                share_weight=Decimal("1.0"),
                is_active=True,
            )
            db.add(prop)
            db.commit()
            db.refresh(prop)

            assert prop.created_at is not None
            assert prop.updated_at is not None
            assert prop.created_at <= prop.updated_at
        finally:
            db.close()
