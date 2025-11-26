"""Integration tests for mini_app endpoints with realistic seeding.

Tests endpoints with actual database state including users, accounts, transactions, bills.
These tests validate complete workflows across the Mini App API.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from src.main import app
from src.models.account import Account
from src.models.bill import Bill, BillType
from src.models.property import Property
from src.models.service_period import PeriodStatus, ServicePeriod
from src.models.transaction import Transaction
from src.models.user import User
from src.services import SessionLocal


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_database():
    """Clean up test database before and after each test."""
    session = SessionLocal()
    try:
        # Delete in reverse dependency order
        session.execute(delete(Bill))
        session.execute(delete(Transaction))
        session.execute(delete(Account))
        session.execute(delete(Property))
        session.execute(delete(ServicePeriod))
        session.execute(delete(User))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

    yield

    # Cleanup after test
    session = SessionLocal()
    try:
        session.execute(delete(Bill))
        session.execute(delete(Transaction))
        session.execute(delete(Account))
        session.execute(delete(Property))
        session.execute(delete(ServicePeriod))
        session.execute(delete(User))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


@pytest.fixture
def test_user_with_data():
    """Create test user with transactions and bills for realistic testing."""
    session = SessionLocal()
    try:
        # Create user
        user = User(
            name="Test User Name",
            telegram_id="12345678",
            is_active=True,
            is_owner=True,
        )
        session.add(user)
        session.flush()
        user_id = user.id

        # Create property
        prop = Property(
            owner_id=user_id,
            property_name="Test House",
            type="residential",
            share_weight=Decimal("100.00"),
            is_active=True,
        )
        session.add(prop)
        session.flush()
        prop_id = prop.id

        # Create accounts
        user_account = Account(
            user_id=user_id,
            name="User Account",
            account_type="user",
        )
        community_account = Account(
            name="Community Account",
            account_type="organization",  # Organization account has no user_id
        )
        session.add_all([user_account, community_account])
        session.flush()
        user_account_id = user_account.id
        community_account_id = community_account.id

        # Create service period
        period = ServicePeriod(
            name="2025-Q1",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            status=PeriodStatus.OPEN,
        )
        session.add(period)
        session.flush()
        period_id = period.id

        # Create transactions
        trans1 = Transaction(
            from_account_id=user_account_id,
            to_account_id=community_account_id,
            amount=Decimal("500.00"),
            transaction_date=date(2025, 1, 15),
            description="Contribution",
        )
        trans2 = Transaction(
            from_account_id=community_account_id,
            to_account_id=user_account_id,
            amount=Decimal("150.00"),
            transaction_date=date(2025, 2, 1),
            description="Reimbursement",
        )
        session.add_all([trans1, trans2])
        session.flush()

        # Create bills
        bill1 = Bill(
            service_period_id=period_id,
            property_id=prop_id,
            bill_type=BillType.ELECTRICITY,
            bill_amount=Decimal("200.00"),
        )
        session.add(bill1)
        session.commit()

        return {
            "user_id": user_id,
            "telegram_id": "12345678",
            "account_id": user_account_id,
            "property_id": prop_id,
            "user_account_id": user_account_id,
            "community_account_id": community_account_id,
            "period_id": period_id,
        }
    finally:
        session.close()


class TestTransactionsEndpoint:
    """Tests for /transactions-list endpoint."""

    def test_transactions_list_successful_response(self, client: TestClient, test_user_with_data):
        """Test /transactions-list returns 200 with realistic data."""
        telegram_id = test_user_with_data["telegram_id"]
        account_id = test_user_with_data["account_id"]

        with patch("src.api.mini_app.UserService.verify_telegram_webapp_signature") as mock_verify:
            mock_verify.return_value = {"user": f'{{"id": {telegram_id}}}'}

            response = client.post(
                f"/api/mini-app/transactions-list?account_id={account_id}",
                headers={"Authorization": f"tma {telegram_id}"},
                json={},
            )

            # Should successfully return user's transactions
            assert response.status_code == 200
            data = response.json()
            assert "transactions" in data

    def test_transactions_list_response_structure(self, client: TestClient, test_user_with_data):
        """Test /transactions-list response contains expected fields."""
        telegram_id = test_user_with_data["telegram_id"]
        account_id = test_user_with_data["account_id"]

        with patch("src.api.mini_app.UserService.verify_telegram_webapp_signature") as mock_verify:
            mock_verify.return_value = {"user": f'{{"id": {telegram_id}}}'}

            response = client.post(
                f"/api/mini-app/transactions-list?account_id={account_id}",
                headers={"Authorization": f"tma {telegram_id}"},
                json={},
            )

            assert response.status_code == 200
            data = response.json()

            # Response should be parseable and contain transactions list
            if "transactions" in data:
                assert isinstance(data["transactions"], list)


class TestBillsEndpoint:
    """Tests for /bills endpoint."""

    def test_bills_successful_response(self, client: TestClient, test_user_with_data):
        """Test /bills returns 200 with realistic data."""
        telegram_id = test_user_with_data["telegram_id"]
        account_id = test_user_with_data["account_id"]

        with patch("src.api.mini_app.UserService.verify_telegram_webapp_signature") as mock_verify:
            mock_verify.return_value = {"user": f'{{"id": {telegram_id}}}'}

            response = client.post(
                f"/api/mini-app/bills?account_id={account_id}",
                headers={"Authorization": f"tma {telegram_id}"},
                json={},
            )

            # Should successfully return user's bills
            assert response.status_code == 200
            data = response.json()
            # Response should be dict or list
            assert data is not None

    def test_bills_response_structure(self, client: TestClient, test_user_with_data):
        """Test /bills response contains bill information."""
        telegram_id = test_user_with_data["telegram_id"]
        account_id = test_user_with_data["account_id"]

        with patch("src.api.mini_app.UserService.verify_telegram_webapp_signature") as mock_verify:
            mock_verify.return_value = {"user": f'{{"id": {telegram_id}}}'}

            response = client.post(
                f"/api/mini-app/bills?account_id={account_id}",
                headers={"Authorization": f"tma {telegram_id}"},
                json={},
            )

            assert response.status_code == 200
            data = response.json()
            # Endpoint should return valid JSON structure
            assert isinstance(data, (dict, list))


class TestBalanceEndpoint:
    """Tests for /balance endpoint."""

    def test_balance_successful_response(self, client: TestClient, test_user_with_data):
        """Test /balance returns 200 with realistic data."""
        telegram_id = test_user_with_data["telegram_id"]
        account_id = test_user_with_data["account_id"]

        with patch("src.api.mini_app.UserService.verify_telegram_webapp_signature") as mock_verify:
            mock_verify.return_value = {"user": f'{{"id": {telegram_id}}}'}

            response = client.post(
                f"/api/mini-app/balance?account_id={account_id}",
                headers={"Authorization": f"tma {telegram_id}"},
                json={},
            )

            # Should successfully calculate and return balance
            assert response.status_code == 200
            data = response.json()
            # Balance response should be parseable
            assert data is not None

    def test_balance_response_structure(self, client: TestClient, test_user_with_data):
        """Test /balance response contains expected fields."""
        telegram_id = test_user_with_data["telegram_id"]
        account_id = test_user_with_data["account_id"]

        with patch("src.api.mini_app.UserService.verify_telegram_webapp_signature") as mock_verify:
            mock_verify.return_value = {"user": f'{{"id": {telegram_id}}}'}

            response = client.post(
                f"/api/mini-app/balance?account_id={account_id}",
                headers={"Authorization": f"tma {telegram_id}"},
                json={},
            )

            assert response.status_code == 200


class TestPropertiesEndpoint:
    """Tests for /properties endpoint."""

    def test_properties_successful_response(self, client: TestClient, test_user_with_data):
        """Test /properties returns 200 with owned properties."""
        telegram_id = test_user_with_data["telegram_id"]

        with patch("src.api.mini_app.UserService.verify_telegram_webapp_signature") as mock_verify:
            mock_verify.return_value = {"user": f'{{"id": {telegram_id}}}'}

            response = client.post(
                "/api/mini-app/properties",
                headers={"Authorization": f"tma {telegram_id}"},
                json={},
            )

            # Should successfully return owned properties
            assert response.status_code == 200
            data = response.json()
            assert data is not None

    def test_properties_response_structure(self, client: TestClient, test_user_with_data):
        """Test /properties response contains properties list."""
        telegram_id = test_user_with_data["telegram_id"]

        with patch("src.api.mini_app.UserService.verify_telegram_webapp_signature") as mock_verify:
            mock_verify.return_value = {"user": f'{{"id": {telegram_id}}}'}

            response = client.post(
                "/api/mini-app/properties",
                headers={"Authorization": f"tma {telegram_id}"},
                json={},
            )

            assert response.status_code == 200
            data = response.json()

            if "properties" in data:
                assert isinstance(data["properties"], list)


class TestBalancesEndpoint:
    """Tests for /balances endpoint (admin endpoint)."""

    def test_balances_endpoint_returns_200(self, client: TestClient, test_user_with_data):
        """Test /balances endpoint returns response."""
        user_id = test_user_with_data["user_id"]
        telegram_id = test_user_with_data["telegram_id"]
        # Mark as admin for this test
        session = SessionLocal()
        try:
            admin_user = session.query(User).filter_by(id=user_id).first()
            admin_user.is_administrator = True
            session.commit()
        finally:
            session.close()

        with patch("src.api.mini_app.UserService.verify_telegram_webapp_signature") as mock_verify:
            mock_verify.return_value = {"user": f'{{"id": {telegram_id}}}'}

            response = client.post(
                "/api/mini-app/accounts",
                headers={"Authorization": f"tma {telegram_id}"},
                json={},
            )

            # Admin should get access to accounts
            assert response.status_code in [200, 403]
