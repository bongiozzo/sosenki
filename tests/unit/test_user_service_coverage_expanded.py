"""Expanded unit tests for UserService to improve coverage."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.services.user_service import UserService, UserStatusService


@pytest.fixture
def user_service(session: AsyncSession):
    """Create UserService with test session."""
    return UserService(session)


@pytest.fixture
def user_status_service(session: AsyncSession):
    """Create UserStatusService with test session."""
    return UserStatusService(session)


@pytest.fixture
def user_service_async(session: AsyncSession):
    """Create UserService for async tests."""
    return UserService(session)


@pytest.fixture
def user_status_service_async(session: AsyncSession):
    """Create UserStatusService for async tests."""
    return UserStatusService(session)


class TestUserStatusServiceGetActiveRoles:
    """Test get_active_roles method for all role combinations."""

    def test_get_active_roles_member_only(self):
        """Verify user with no roles returns ['member']."""
        user = User(name="Basic User", is_active=True)
        roles = UserStatusService.get_active_roles(user)
        assert roles == ["member"]

    def test_get_active_roles_multiple_roles(self):
        """Verify user with multiple roles returns all roles sorted."""
        user = User(
            name="Multi User",
            is_administrator=True,
            is_investor=True,
            is_owner=True,
            is_active=True,
        )
        roles = UserStatusService.get_active_roles(user)
        assert "administrator" in roles
        assert "investor" in roles
        assert "owner" in roles
        assert roles == sorted(roles)

    def test_get_active_roles_all_roles(self):
        """Verify user with all roles."""
        user = User(
            name="Super User",
            is_administrator=True,
            is_investor=True,
            is_owner=True,
            is_staff=True,
            is_stakeholder=True,
            is_tenant=True,
            is_active=True,
        )
        roles = UserStatusService.get_active_roles(user)
        assert set(roles) == {
            "administrator",
            "investor",
            "owner",
            "staff",
            "stakeholder",
            "tenant",
        }


@pytest.mark.asyncio
class TestUserStatusServiceGetRepresentedUser:
    """Test get_represented_user method."""

    async def test_get_represented_user_no_representative(self, user_status_service_async):
        """Verify user with no representative_id returns None."""
        user = User(name="Solo User", telegram_id="111", is_active=True)
        user_status_service_async.session.add(user)
        await user_status_service_async.session.commit()

        result = await user_status_service_async.get_represented_user(user.id)
        assert result is None

    async def test_get_represented_user_nonexistent_user(self, user_status_service_async):
        """Verify nonexistent user returns None."""
        result = await user_status_service_async.get_represented_user(99999)
        assert result is None

    async def test_get_represented_user_valid(self, user_status_service_async):
        """Verify user with valid representative returns represented user."""
        represented = User(name="Represented User", telegram_id="222", is_active=True)
        user_status_service_async.session.add(represented)
        await user_status_service_async.session.commit()

        representing = User(
            name="Representing User",
            telegram_id="111",
            representative_id=represented.id,
            is_active=True,
        )
        user_status_service_async.session.add(representing)
        await user_status_service_async.session.commit()

        result = await user_status_service_async.get_represented_user(representing.id)
        assert result is not None
        assert result.id == represented.id
        assert result.name == "Represented User"


@pytest.mark.asyncio
class TestUserServiceMethods:
    """Test UserService access methods."""

    async def test_can_access_mini_app_active_user(self, user_service_async):
        """Verify active user can access mini app."""
        user = User(name="Active User", telegram_id="444", is_active=True)
        user_service_async.session.add(user)
        await user_service_async.session.commit()

        can_access = await user_service_async.can_access_mini_app("444")
        assert can_access is True

    async def test_can_access_mini_app_inactive_user(self, user_service_async):
        """Verify inactive user cannot access mini app."""
        user = User(name="Inactive User", telegram_id="555", is_active=False)
        user_service_async.session.add(user)
        await user_service_async.session.commit()

        can_access = await user_service_async.can_access_mini_app("555")
        assert can_access is False

    async def test_can_access_invest_investor(self, user_service_async):
        """Verify investor can access invest features."""
        user = User(name="Investor", telegram_id="666", is_active=True, is_investor=True)
        user_service_async.session.add(user)
        await user_service_async.session.commit()

        can_access = await user_service_async.can_access_invest("666")
        assert can_access is True

    async def test_can_access_invest_non_investor(self, user_service_async):
        """Verify non-investor cannot access invest features."""
        user = User(name="Non-Investor", telegram_id="777", is_active=True, is_investor=False)
        user_service_async.session.add(user)
        await user_service_async.session.commit()

        can_access = await user_service_async.can_access_invest("777")
        assert can_access is False

    async def test_is_administrator_true(self, user_service_async):
        """Verify administrator check."""
        user = User(name="Admin", telegram_id="888", is_active=True, is_administrator=True)
        user_service_async.session.add(user)
        await user_service_async.session.commit()

        is_admin = await user_service_async.is_administrator("888")
        assert is_admin is True

    async def test_is_administrator_false(self, user_service_async):
        """Verify non-administrator check."""
        user = User(name="Regular", telegram_id="999", is_active=True, is_administrator=False)
        user_service_async.session.add(user)
        await user_service_async.session.commit()

        is_admin = await user_service_async.is_administrator("999")
        assert is_admin is False
