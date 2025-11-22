"""Test seeding configuration loading."""

import pytest

from seeding.config.seeding_config import SeedingConfig


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
    assert defaults["is_active"] is False


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
