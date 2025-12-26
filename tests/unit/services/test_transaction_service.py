from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from src.models.account import Account, AccountType
from src.models.audit_log import AuditLog
from src.services.transaction_service import TransactionService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_suggested_amount_owner_to_org_rounds_debt(session, monkeypatch):
    owner = Account(name="Owner", account_type=AccountType.OWNER)
    org = Account(name="Org", account_type=AccountType.ORGANIZATION)
    session.add_all([owner, org])
    await session.commit()

    service = TransactionService(session)

    async def fake_balance(account_id: int):  # noqa: ARG001
        return Decimal("12499")

    monkeypatch.setattr(service.balance_service, "calculate_account_balance", fake_balance)

    suggested = await service.calculate_suggested_amount(owner, org)
    assert suggested == 15000  # ceil to nearest 5000


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_suggested_amount_last_transaction_used(session):
    a1 = Account(name="A1", account_type=AccountType.STAFF)
    a2 = Account(name="A2", account_type=AccountType.STAFF)
    session.add_all([a1, a2])
    await session.flush()

    # Insert last transaction amount
    from datetime import date

    from src.models.transaction import (
        Transaction,  # local import to avoid circulars in test collection
    )

    tx = Transaction(
        from_account_id=a1.id,
        to_account_id=a2.id,
        amount=Decimal("321"),
        transaction_date=date.today(),
    )
    session.add(tx)
    await session.commit()

    service = TransactionService(session)
    suggested = await service.calculate_suggested_amount(a1, a2)
    assert suggested == 321


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_description_formats_amount(session):  # noqa: ARG001
    a1 = Account(name="Alice", account_type=AccountType.STAFF)
    a2 = Account(name="Bob", account_type=AccountType.ORGANIZATION)
    service = TransactionService(session)
    desc = service.generate_description(a1, a2, Decimal("35000"))
    normalized = desc.replace("\u00a0", " ")
    assert "Alice" in normalized and "Bob" in normalized and "35 000" in normalized


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_transaction_success_persists_and_audits(session):
    a1 = Account(name="From", account_type=AccountType.STAFF)
    a2 = Account(name="To", account_type=AccountType.ORGANIZATION)
    session.add_all([a1, a2])
    await session.commit()

    service = TransactionService(session)
    tx = await service.create_transaction(
        from_account_id=a1.id,
        to_account_id=a2.id,
        amount=Decimal("123.45"),
        description="test tx",
        actor_id=42,
        transaction_date=date(2025, 1, 1),
    )
    await session.commit()

    # Transaction stored
    fetched = await session.get(type(tx), tx.id)
    assert fetched is not None and fetched.amount == Decimal("123.45")
    assert fetched.transaction_date == date(2025, 1, 1)

    # Audit log stored
    audit_rows = (await session.execute(select(AuditLog))).scalars().all()
    assert len(audit_rows) == 1
    assert audit_rows[0].actor_id == 42


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_transaction_invalid_amount_raises(session):
    service = TransactionService(session)
    with pytest.raises(ValueError):
        await service.create_transaction(
            from_account_id=1,
            to_account_id=2,
            amount=Decimal("0"),
            description="bad",
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_transaction_missing_account_raises(session):
    service = TransactionService(session)
    with pytest.raises(ValueError):
        await service.create_transaction(
            from_account_id=999,
            to_account_id=1000,
            amount=Decimal("10"),
            description="missing",
            transaction_date=date(2025, 1, 1),
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_transaction_defaults_to_today(session):
    a1 = Account(name="From", account_type=AccountType.STAFF)
    a2 = Account(name="To", account_type=AccountType.ORGANIZATION)
    session.add_all([a1, a2])
    await session.commit()

    service = TransactionService(session)
    tx = await service.create_transaction(
        from_account_id=a1.id,
        to_account_id=a2.id,
        amount=Decimal("50"),
        description="default date",
        actor_id=5,
    )
    await session.commit()

    assert tx.transaction_date == date.today()
