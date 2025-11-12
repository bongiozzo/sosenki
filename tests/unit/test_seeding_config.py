"""Test seeding configuration loading."""

import pytest

from src.config.seeding_config import SeedingConfig


def test_seeding_config_loads():
    """Test that seeding configuration loads successfully."""
    config = SeedingConfig.load()
    assert config is not None


def test_user_defaults():
    """Test user defaults configuration."""
    config = SeedingConfig.load()
    defaults = config.get_user_defaults()

    assert defaults["is_investor"] is True
    assert defaults["is_owner"] is True
    assert defaults["is_administrator"] is False
    assert defaults["is_active"] is False


def test_user_special_rules():
    """Test special user rules configuration."""
    config = SeedingConfig.load()

    # Check П special rule
    polyakov_rule = config.get_user_special_rule("П")
    assert polyakov_rule is not None
    assert polyakov_rule["is_administrator"] is True
    assert polyakov_rule["username"] == "Bongiozzo"
    assert polyakov_rule["telegram_id"] == 73517108

    # Check non-existent user returns None
    other_rule = config.get_user_special_rule("OtherUser")
    assert other_rule is None


def test_property_type_mapping():
    """Test DOP type mapping configuration."""
    config = SeedingConfig.load()
    mapping = config.get_property_type_mapping()

    assert mapping["26"] == "Малый"
    assert mapping["4"] == "Беседка"
    assert mapping["49"] == "Склад"
    assert mapping["69"] == "Хоздвор"


def test_property_default_type():
    """Test default property type for unmapped codes."""
    config = SeedingConfig.load()
    default_type = config.get_property_default_type()

    assert default_type == "Баня"


def test_property_field_mappings():
    """Test property field mappings configuration."""
    config = SeedingConfig.load()
    mappings = config.get_property_field_mappings("main")

    assert mappings["property_name_column"] == "Дом"
    assert mappings["type_column"] == "Размер"
    assert mappings["share_weight_column"] == "Коэффициент"


def test_user_parsing_rules():
    """Test user parsing rules configuration."""
    config = SeedingConfig.load()
    rules = config.get_user_parsing_rules()

    assert rules["name_column"] == "Фамилия"
    assert rules["stakeholder_column"] == "Доля в Т"


def test_dop_source_column():
    """Test DOP source column configuration."""
    config = SeedingConfig.load()
    dop_column = config.get_dop_source_column()

    assert dop_column == "Доп"


def test_inherited_and_null_fields():
    """Test inherited and null fields configuration."""
    config = SeedingConfig.load()
    inherited = config.get_inherited_fields()
    null_fields = config.get_null_fields()

    assert "is_ready" in inherited
    assert "is_for_tenant" in inherited
    assert "share_weight" in null_fields
    assert "photo_link" in null_fields


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
