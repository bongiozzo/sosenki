"""Unit tests for src.services.auth_service."""

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.models.account import Account, AccountType
from src.services.auth_service import (
    AuthorizedUser,
    authorize_account_access,
    authorize_account_access_for_roles,
    authorize_user_context_access,
    get_authenticated_user,
    resolve_target_user,
    verify_telegram_auth,
)


@dataclass
class DummyUser:
    id: int
    telegram_id: int
    is_active: bool = True
    is_administrator: bool = False
    is_owner: bool = False
    is_staff: bool = False
    representative_id: int | None = None


@pytest.fixture
def async_session():
    session = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def active_user():
    return DummyUser(id=1, telegram_id=111, is_active=True)


@pytest.fixture
def admin_user():
    return DummyUser(id=2, telegram_id=222, is_active=True, is_administrator=True)


@pytest.fixture
def owner_user():
    return DummyUser(id=3, telegram_id=333, is_active=True, is_owner=True)


@pytest.mark.asyncio
async def test_verify_telegram_auth_missing_data(async_session):
    with pytest.raises(HTTPException) as exc:
        await verify_telegram_auth(async_session)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_telegram_auth_invalid_signature(async_session):
    with patch(
        "src.services.auth_service.UserService.verify_telegram_webapp_signature",
        return_value=None,
    ):
        with pytest.raises(HTTPException) as exc:
            await verify_telegram_auth(async_session, authorization="tma raw-data")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_telegram_auth_success(async_session):
    with patch(
        "src.services.auth_service.UserService.verify_telegram_webapp_signature",
        return_value={"user": '{"id": 555}'},
    ):
        telegram_id = await verify_telegram_auth(async_session, authorization="tma valid")
    assert telegram_id == 555


@pytest.mark.asyncio
async def test_get_authenticated_user_active(async_session, active_user):
    with patch("src.services.auth_service.UserService") as mock_service:
        instance = MagicMock()
        instance.get_by_telegram_id = AsyncMock(return_value=active_user)
        mock_service.return_value = instance
        user = await get_authenticated_user(async_session, telegram_id=111)
    assert user == active_user


@pytest.mark.asyncio
async def test_get_authenticated_user_inactive(async_session):
    inactive_user = DummyUser(id=10, telegram_id=999, is_active=False)
    with patch("src.services.auth_service.UserService") as mock_service:
        instance = MagicMock()
        instance.get_by_telegram_id = AsyncMock(return_value=inactive_user)
        mock_service.return_value = instance
        with pytest.raises(HTTPException) as exc:
            await get_authenticated_user(async_session, telegram_id=999)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_resolve_target_user_admin_switch(async_session, admin_user):
    selected_user = DummyUser(id=5, telegram_id=555)
    async_session.get.return_value = selected_user
    target, switched = await resolve_target_user(async_session, admin_user, selected_user_id=5)
    assert target == selected_user
    assert switched is True
    async_session.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_target_user_admin_switch_not_found(async_session, admin_user):
    async_session.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await resolve_target_user(async_session, admin_user, selected_user_id=99)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_resolve_target_user_representation(async_session, active_user):
    active_user.representative_id = 42
    represented_user = DummyUser(id=7, telegram_id=777)
    with patch("src.services.auth_service.UserStatusService") as mock_status:
        status_instance = MagicMock()
        status_instance.get_represented_user = AsyncMock(return_value=represented_user)
        mock_status.return_value = status_instance
        target, switched = await resolve_target_user(async_session, active_user)
    assert target == represented_user
    assert switched is True


@pytest.mark.asyncio
async def test_authorize_user_context_access_missing_role(async_session, active_user):
    with pytest.raises(HTTPException) as exc:
        await authorize_user_context_access(
            async_session,
            authenticated_user=active_user,
            required_role="is_owner",
        )
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_authorize_user_context_access_success(async_session, admin_user):
    target_user = DummyUser(id=10, telegram_id=1010)
    with patch(
        "src.services.auth_service.resolve_target_user",
        return_value=(target_user, True),
    ):
        authorized = await authorize_user_context_access(
            async_session,
            authenticated_user=admin_user,
            required_role=None,
            selected_user_id=10,
        )
    assert isinstance(authorized, AuthorizedUser)
    assert authorized.target_user == target_user
    assert authorized.switched_context is True


@pytest.mark.asyncio
async def test_authorize_account_access_invalid_id(async_session, active_user):
    with pytest.raises(HTTPException) as exc:
        await authorize_account_access(async_session, active_user, account_id=0)
    assert exc.value.status_code == 400


def _mock_account(account_id=1, user_id=1, account_type=AccountType.OWNER):
    account = MagicMock(spec=Account)
    account.id = account_id
    account.user_id = user_id
    account.account_type = account_type
    return account


def _set_account_query_result(session, account):
    result = MagicMock()
    result.scalar_one_or_none.return_value = account
    session.execute = AsyncMock(return_value=result)


@pytest.mark.asyncio
async def test_authorize_account_access_not_found(async_session, active_user):
    _set_account_query_result(async_session, None)
    with pytest.raises(HTTPException) as exc:
        await authorize_account_access(async_session, active_user, account_id=1)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_authorize_account_access_admin(async_session, admin_user):
    account = _mock_account(user_id=999)
    _set_account_query_result(async_session, account)
    result = await authorize_account_access(async_session, admin_user, account_id=5)
    assert result == account


@pytest.mark.asyncio
async def test_authorize_account_access_owner_shared(async_session, owner_user):
    account = _mock_account(account_type=AccountType.ORGANIZATION)
    _set_account_query_result(async_session, account)
    result = await authorize_account_access(async_session, owner_user, account_id=5)
    assert result == account


@pytest.mark.asyncio
async def test_authorize_account_access_unauthorized(async_session, active_user):
    account = _mock_account(user_id=999, account_type=AccountType.STAFF)
    _set_account_query_result(async_session, account)
    with pytest.raises(HTTPException) as exc:
        await authorize_account_access(async_session, active_user, account_id=5)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_authorize_account_access_for_roles_invalid_id(async_session, active_user):
    with pytest.raises(HTTPException) as exc:
        await authorize_account_access_for_roles(async_session, active_user, 0, ["is_owner"])
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_authorize_account_access_for_roles_not_found(async_session, active_user):
    _set_account_query_result(async_session, None)
    with pytest.raises(HTTPException) as exc:
        await authorize_account_access_for_roles(async_session, active_user, 1, ["is_owner"])
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_authorize_account_access_for_roles_missing_role(async_session, active_user):
    account = _mock_account()
    _set_account_query_result(async_session, account)
    with pytest.raises(HTTPException) as exc:
        await authorize_account_access_for_roles(async_session, active_user, 1, ["is_owner"])
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_authorize_account_access_for_roles_success(async_session, owner_user):
    account = _mock_account()
    _set_account_query_result(async_session, account)
    result = await authorize_account_access_for_roles(async_session, owner_user, 1, ["is_owner"])
    assert result == account
