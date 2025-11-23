"""Pytest configuration for tests - applies migrations automatically."""

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Set test database URL BEFORE any imports from src
# This ensures the SessionLocal and engine use the test database
os.environ["DATABASE_URL"] = "sqlite:///./test_sosenki.db"

# Set dummy test token for TELEGRAM_BOT_TOKEN (required by bot config validation)
# This is only used for unit/contract tests that don't make actual API calls
os.environ["TELEGRAM_BOT_TOKEN"] = "test_token_1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Set test mini app URL (required for application startup)
os.environ["MINI_APP_URL"] = "http://localhost:3000/mini-app/"

# Set seeding config path (required for seeding tests)
os.environ["SEEDING_CONFIG_PATH"] = "seeding/config/seeding.json"

# Get the project root directory
project_root = Path(__file__).parent.parent

# Apply migrations immediately on test startup
try:
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "DATABASE_URL": "sqlite:///./test_sosenki.db"},
    )

    if result.returncode != 0:
        print(
            f"WARNING: Alembic migration failed with return code {result.returncode}",
            file=sys.stderr,
        )
        print("STDOUT:", result.stdout, file=sys.stderr)
        print("STDERR:", result.stderr, file=sys.stderr)
    else:
        print("✓ Applied migrations to test database", file=sys.stderr)
except subprocess.TimeoutExpired:
    print("WARNING: Alembic migration timed out", file=sys.stderr)
except Exception as e:
    print(f"WARNING: Failed to apply migrations: {e}", file=sys.stderr)


# NOW safe to import from src (after env vars set)
from src.models import Base  # noqa: E402
from src.models.account import Account  # noqa: E402
from src.models.service_period import ServicePeriod  # noqa: E402
from src.models.user import User  # noqa: E402


@pytest.fixture
async def async_engine():
    """Create an async test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(async_engine):
    """Create an async session for tests."""
    async_session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def sample_user(session: AsyncSession):
    """Create a sample user for tests."""
    user = User(name="Test User", telegram_id="123456789", is_active=True)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
async def another_user(session: AsyncSession):
    """Create another sample user for tests."""
    user = User(name="Another User", telegram_id="987654321", is_active=True)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
async def sample_account(session: AsyncSession, sample_user: User):
    """Create a sample account for tests."""
    account = Account(
        name="Test Account",
        user_id=sample_user.id,
        account_type="user",
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


@pytest.fixture
async def service_period(session: AsyncSession):
    """Create a service period for tests."""
    period = ServicePeriod(
        name="2024-Q1",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
    )
    session.add(period)
    await session.commit()
    await session.refresh(period)
    return period
