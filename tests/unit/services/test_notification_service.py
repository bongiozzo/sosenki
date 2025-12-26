from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.account import Account, AccountType
from src.models.user import User
from src.services.notification_service import NotificationService


class DummyBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        self.sent.append({"chat_id": chat_id, "text": text, "parse_mode": parse_mode})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notify_account_owners_and_representatives_sends_to_owner_and_rep(
    session: AsyncSession,
):
    bot = DummyBot()
    app = SimpleNamespace(bot=bot)
    notifier = NotificationService(app)

    owner = User(name="Owner", telegram_id=111, is_active=True, is_owner=True)
    rep = User(name="Representative", telegram_id=222, is_active=True)
    session.add_all([owner, rep])
    await session.flush()

    rep.representative_id = owner.id
    await session.flush()

    account = Account(name="Owner Account", account_type=AccountType.OWNER, user_id=owner.id)
    session.add(account)
    await session.commit()

    await notifier.notify_account_owners_and_representatives(
        session=session,
        account_ids=[account.id],
        text="hello",
    )

    assert {m["chat_id"] for m in bot.sent} == {111, 222}
    assert all(m["text"] == "hello" for m in bot.sent)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notify_account_owners_and_representatives_skips_inactive_and_skips_admin(
    session: AsyncSession,
):
    bot = DummyBot()
    app = SimpleNamespace(bot=bot)
    notifier = NotificationService(app)

    owner = User(name="Owner2", telegram_id=333, is_active=True, is_owner=True)
    inactive_rep = User(name="InactiveRep", telegram_id=444, is_active=False)
    active_rep = User(name="ActiveRep", telegram_id=555, is_active=True)
    session.add_all([owner, inactive_rep, active_rep])
    await session.flush()

    inactive_rep.representative_id = owner.id
    active_rep.representative_id = owner.id
    await session.flush()

    account = Account(name="Owner Account 2", account_type=AccountType.OWNER, user_id=owner.id)
    session.add(account)
    await session.commit()

    await notifier.notify_account_owners_and_representatives(
        session=session,
        account_ids=[account.id],
        text="world",
        skip_telegram_id=333,  # admin telegram_id
    )

    # Should notify only active_rep (555); owner skipped by skip_telegram_id; inactive rep skipped
    assert {m["chat_id"] for m in bot.sent} == {555}
    assert all(m["text"] == "world" for m in bot.sent)
