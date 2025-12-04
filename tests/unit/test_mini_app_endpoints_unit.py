"""Unit tests for mini app endpoint functions with mocked dependencies."""

from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.mini_app import (
    AccountResponse,
    AccountsResponse,
    BillsResponse,
    InitResponse,
    PropertiesResponse,
    TransactionsResponse,
    UserContextResponse,
    get_account,
    get_accounts,
    get_bills,
    get_properties,
    get_transactions,
    get_user_context,
    init,
)


@pytest.fixture
def async_session():
    """Provide a reusable AsyncSession stub."""
    session = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_init_endpoint_success(async_session):
    """Verify init endpoint flows through dependencies."""
    auth_user = SimpleNamespace(
        id=1,
        name="Admin",
        is_administrator=True,
        representative_id=10,
    )
    target_user = SimpleNamespace(id=2, name="Target")
    auth_context = SimpleNamespace(authenticated_user=auth_user, target_user=target_user)
    init_response = InitResponse(
        name="Admin",
        is_administrator=True,
        representative_id=10,
        user_context=None,
        users=None,
        stakeholder_url=None,
        photo_gallery_url=None,
    )

    with (
        patch(
            "src.api.mini_app.verify_telegram_auth",
            new=AsyncMock(return_value=111),
        ),
        patch(
            "src.api.mini_app.get_authenticated_user",
            new=AsyncMock(return_value=auth_user),
        ),
        patch(
            "src.api.mini_app.authorize_user_context_access",
            new=AsyncMock(return_value=auth_context),
        ),
        patch(
            "src.api.mini_app._init_build_response",
            new=AsyncMock(return_value=init_response),
        ),
    ):
        response = await init(selected_user_id=2, session=async_session, authorization="tma x")

    assert response == init_response


@pytest.mark.asyncio
async def test_get_user_context_success(async_session):
    """Admins can fetch selected user context."""
    target_user = SimpleNamespace(id=5, name="Selected")
    async_session.get = AsyncMock(return_value=target_user)
    context_response = UserContextResponse(
        user_id=5, name="Selected", account_id=9, roles=["owner"]
    )

    with (
        patch(
            "src.api.mini_app.verify_telegram_auth",
            new=AsyncMock(return_value=222),
        ),
        patch(
            "src.api.mini_app.get_authenticated_user",
            new=AsyncMock(return_value=SimpleNamespace(is_administrator=True)),
        ),
        patch(
            "src.api.mini_app.authorize_user_context_access",
            new=AsyncMock(),
        ),
        patch(
            "src.api.mini_app._build_user_context_data",
            new=AsyncMock(return_value=context_response),
        ),
    ):
        response = await get_user_context(
            selected_user_id=5,
            session=async_session,
            authorization="tma",
        )

    assert isinstance(response, UserContextResponse)
    assert response.user_id == 5


@pytest.mark.asyncio
async def test_get_user_context_not_found(async_session):
    """Endpoint raises 404 when selected user missing."""
    async_session.get = AsyncMock(return_value=None)

    with (
        patch(
            "src.api.mini_app.verify_telegram_auth",
            new=AsyncMock(return_value=123),
        ),
        patch(
            "src.api.mini_app.get_authenticated_user",
            new=AsyncMock(return_value=SimpleNamespace(is_administrator=True)),
        ),
        patch(
            "src.api.mini_app.authorize_user_context_access",
            new=AsyncMock(),
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await get_user_context(selected_user_id=99, session=async_session, authorization="tma")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_properties_returns_response(async_session):
    """Owner context returns formatted properties."""
    property_obj = SimpleNamespace(
        id=101,
        property_name="Main",
        type="apartment",
        share_weight="100",
        is_ready=True,
        is_for_tenant=False,
        photo_link="https://",
        sale_price="500000",
        main_property_id=None,
    )
    scalars = MagicMock()
    scalars.all.return_value = [property_obj]
    result = MagicMock()
    result.scalars.return_value = scalars
    async_session.execute = AsyncMock(return_value=result)

    auth_user = SimpleNamespace(is_owner=True)
    auth_context = SimpleNamespace(target_user=SimpleNamespace(id=42))

    with (
        patch(
            "src.api.mini_app.verify_telegram_auth",
            new=AsyncMock(return_value=777),
        ),
        patch(
            "src.api.mini_app.get_authenticated_user",
            new=AsyncMock(return_value=auth_user),
        ),
        patch(
            "src.api.mini_app.authorize_user_context_access",
            new=AsyncMock(return_value=auth_context),
        ),
    ):
        response = await get_properties(session=async_session, authorization="tma")

    assert isinstance(response, PropertiesResponse)
    assert response.total_count == 1
    assert response.properties[0].property_name == "Main"


@pytest.mark.asyncio
async def test_get_transactions_personal_scope(async_session):
    """Transactions endpoint formats rows into response objects."""
    row = (
        1,
        "Owner",
        2,
        "Org",
        150.75,
        datetime(2025, 1, 5, 12, 0, 0),
        "Monthly payment",
    )
    result = MagicMock()
    result.all.return_value = [row]
    async_session.execute = AsyncMock(return_value=result)

    with (
        patch(
            "src.api.mini_app.verify_telegram_auth",
            new=AsyncMock(return_value=555),
        ),
        patch(
            "src.api.mini_app.get_authenticated_user",
            new=AsyncMock(return_value=SimpleNamespace()),
        ),
        patch(
            "src.api.mini_app.authorize_account_access",
            new=AsyncMock(),
        ),
    ):
        response = await get_transactions(
            account_id=10,
            scope="personal",
            authorization="tma",
            db=async_session,
        )

    assert isinstance(response, TransactionsResponse)
    assert response.transactions[0].amount == 150.75
    assert response.transactions[0].date.startswith("2025-01-05")


@pytest.mark.asyncio
async def test_get_bills_returns_electricity_data(async_session):
    """Bills endpoint joins period and property data."""
    account = SimpleNamespace(user_id=50)

    properties_result = MagicMock()
    properties_result.all.return_value = [(201,), (202,)]

    bill = SimpleNamespace(
        comment="",
        bill_amount=300,
        bill_type=SimpleNamespace(value="electricity"),
    )
    service_period = SimpleNamespace(
        name="2025-01",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
    )
    property_obj = SimpleNamespace(property_name="Villa", type="house")
    bills_result = MagicMock()
    bills_result.all.return_value = [(bill, service_period, property_obj, 100.0, 150.0)]

    async_session.execute = AsyncMock(side_effect=[properties_result, bills_result])

    with (
        patch(
            "src.api.mini_app.verify_telegram_auth",
            new=AsyncMock(return_value=888),
        ),
        patch(
            "src.api.mini_app.get_authenticated_user",
            new=AsyncMock(return_value=SimpleNamespace()),
        ),
        patch(
            "src.api.mini_app.authorize_account_access",
            new=AsyncMock(return_value=account),
        ),
    ):
        response = await get_bills(account_id=3, authorization="tma", db=async_session)

    assert isinstance(response, BillsResponse)
    assert response.bills[0].consumption == 50.0
    assert response.bills[0].property_name == "Villa"


@pytest.mark.asyncio
async def test_get_account_returns_balance(async_session):
    """Account endpoint returns balance calculation."""
    balance_result = SimpleNamespace(balance=123.45, invert_for_display=False)

    with (
        patch(
            "src.api.mini_app.verify_telegram_auth",
            new=AsyncMock(return_value=999),
        ),
        patch(
            "src.api.mini_app.get_authenticated_user",
            new=AsyncMock(return_value=SimpleNamespace()),
        ),
        patch(
            "src.api.mini_app.authorize_account_access",
            new=AsyncMock(),
        ),
        patch(
            "src.services.balance_service.BalanceCalculationService",
        ) as mock_balance,
    ):
        balance_instance = MagicMock()
        balance_instance.calculate_account_balance_with_display = AsyncMock(
            return_value=balance_result
        )
        mock_balance.return_value = balance_instance

        response = await get_account(account_id=7, authorization="tma", session=async_session)

    assert isinstance(response, AccountResponse)
    assert response.balance == 123.45


@pytest.mark.asyncio
async def test_get_accounts_lists_all_accounts(async_session):
    """Accounts endpoint aggregates balances for each account."""
    accounts = [
        SimpleNamespace(
            id=1,
            name="Owner",
            account_type=SimpleNamespace(value="owner"),
            user=SimpleNamespace(representative_id=None),
        ),
        SimpleNamespace(id=2, name="Org", account_type="organization", user=None),
    ]
    scalars = MagicMock()
    scalars.all.return_value = accounts
    result = MagicMock()
    result.scalars.return_value = scalars
    async_session.execute = AsyncMock(return_value=result)

    balance_results = [
        SimpleNamespace(balance=100.0, invert_for_display=False),
        SimpleNamespace(balance=-50.0, invert_for_display=True),
    ]

    with (
        patch(
            "src.api.mini_app.verify_telegram_auth",
            new=AsyncMock(return_value=321),
        ),
        patch(
            "src.api.mini_app.get_authenticated_user",
            new=AsyncMock(return_value=SimpleNamespace()),
        ),
        patch(
            "src.api.mini_app.authorize_account_access_for_roles",
            new=AsyncMock(),
        ),
        patch(
            "src.services.balance_service.BalanceCalculationService",
        ) as mock_balance,
    ):
        balance_instance = MagicMock()
        balance_instance.calculate_account_balance_with_display = AsyncMock(
            side_effect=balance_results
        )
        mock_balance.return_value = balance_instance

        response = await get_accounts(authorization="tma", session=async_session)

    assert isinstance(response, AccountsResponse)
    assert len(response.accounts) == 2
    assert response.accounts[0].account_type == "owner"
    assert response.accounts[1].invert_for_display is True
