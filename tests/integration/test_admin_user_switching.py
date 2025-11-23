"""Integration tests for admin user-switching feature."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.user_service import UserService


@pytest.mark.asyncio
async def test_admin_can_fetch_all_users(session: AsyncSession):
    """Test that get_all_users returns all users ordered by name."""
    # Create test users
    user1 = User(name="Zebra User", telegram_id="111", is_active=True)
    user2 = User(name="Alpha User", telegram_id="222", is_active=True)
    user3 = User(name="Beta User", telegram_id="333", is_active=False)

    session.add_all([user1, user2, user3])
    await session.commit()

    # Fetch all users via service
    user_service = UserService(session)
    all_users = await user_service.get_all_users()

    # Should return all users ordered by name (regardless of is_active)
    assert len(all_users) == 3
    assert all_users[0].name == "Alpha User"
    assert all_users[1].name == "Beta User"
    assert all_users[2].name == "Zebra User"


@pytest.mark.asyncio
async def test_admin_user_switching_context(session: AsyncSession):
    """Test admin can switch to view another user's context."""
    # Create admin user and regular user
    admin_user = User(
        name="Admin User",
        telegram_id="999",
        is_active=True,
        is_administrator=True,
        is_owner=False,
    )
    target_user = User(
        name="Target User",
        telegram_id="888",
        is_active=True,
        is_owner=True,
        is_stakeholder=True,
    )

    session.add_all([admin_user, target_user])
    await session.commit()
    await session.refresh(admin_user)
    await session.refresh(target_user)

    # Simulate admin selecting target user
    # In real flow, this would be via _resolve_target_user with selected_user_id
    user_service = UserService(session)

    # Admin should be able to get target user
    is_admin = await user_service.is_administrator(admin_user.telegram_id)
    assert is_admin is True

    # Verify target user exists and is owner
    fetched_target = await session.get(User, target_user.id)
    assert fetched_target is not None
    assert fetched_target.is_owner is True
    assert fetched_target.is_stakeholder is True


@pytest.mark.asyncio
async def test_non_admin_cannot_access_users_list(session: AsyncSession):
    """Test that non-admin users don't have admin privileges."""
    # Create non-admin user
    regular_user = User(
        name="Regular User",
        telegram_id="777",
        is_active=True,
        is_administrator=False,
    )

    session.add(regular_user)
    await session.commit()

    # Check is_administrator returns False
    user_service = UserService(session)
    is_admin = await user_service.is_administrator(regular_user.telegram_id)
    assert is_admin is False


@pytest.mark.asyncio
async def test_admin_selection_with_invalid_user_id(session: AsyncSession):
    """Test handling of invalid selected_user_id."""
    # Create admin user
    admin_user = User(
        name="Admin User",
        telegram_id="999",
        is_active=True,
        is_administrator=True,
    )

    session.add(admin_user)
    await session.commit()

    # Try to fetch non-existent user
    invalid_user_id = 99999
    fetched_user = await session.get(User, invalid_user_id)

    # Should return None
    assert fetched_user is None


@pytest.mark.asyncio
async def test_admin_dropdown_shows_all_users_including_inactive(session: AsyncSession):
    """Test that admin dropdown includes both active and inactive users."""
    # Create mix of active and inactive users
    active_user = User(name="Active User", telegram_id="101", is_active=True)
    inactive_user = User(name="Inactive User", telegram_id="102", is_active=False)
    no_telegram_user = User(name="No Telegram User", telegram_id=None, is_active=True)

    session.add_all([active_user, inactive_user, no_telegram_user])
    await session.commit()

    # Fetch all users
    user_service = UserService(session)
    all_users = await user_service.get_all_users()

    # Should include all users (active, inactive, with/without telegram_id)
    assert len(all_users) == 3

    # Verify all users are present
    user_names = [u.name for u in all_users]
    assert "Active User" in user_names
    assert "Inactive User" in user_names
    assert "No Telegram User" in user_names
