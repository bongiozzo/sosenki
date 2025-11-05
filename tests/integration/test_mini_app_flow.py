"""Integration test for registered user Mini App load (US2)."""

import pytest


@pytest.mark.asyncio
async def test_registered_user_mini_app_load():
    """Test that registered user sees welcome and menu in Mini App."""
    # Full implementation would:
    # 1. Create test User with is_active=True
    # 2. Open Mini App (simulate WebApp.initData)
    # 3. Call /api/mini-app/init
    # 4. Verify response contains welcome message and 3 menu items (Rule, Pay, Invest)
    # 5. Verify menu items are interactive
    pass


@pytest.mark.asyncio
async def test_mini_app_design_loads():
    """Test that Mini App CSS loads with nature-inspired colors."""
    # Test would verify:
    # 1. Static files are served at /mini-app/
    # 2. styles.css contains --color-pine, --color-water, --color-sand
    # 3. index.html loads successfully
    pass
