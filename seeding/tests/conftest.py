"""Pytest configuration for seeding tests - applies migrations automatically.

Database Strategy for Seeding/Data Integrity Tests:
- In dev (ENV=dev): Uses sosenki.dev.db (development seeded database)
- In prod (ENV=prod): Uses sosenki.db (production seeded database)
- Purpose: Data integrity tests verify that Google Sheets data is correctly imported
- Workflow: make seed → populates database → make test-seeding → verifies data integrity
- Note: For unit/integration tests, see tests/conftest.py which uses test_sosenki.db for isolation
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load .env file (same as Makefile does with "include .env")
# This ensures seeding tests use the same environment configuration
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Get the project root directory
project_root = Path(__file__).parent.parent.parent

# Apply migrations immediately on test startup
try:
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=30,
        env=os.environ.copy(),
    )

    if result.returncode != 0:
        print(
            f"WARNING: Alembic migration failed with return code {result.returncode}",
            file=sys.stderr,
        )
        print("STDOUT:", result.stdout, file=sys.stderr)
        print("STDERR:", result.stderr, file=sys.stderr)
    else:
        print(f"✓ Applied migrations to {os.environ['DATABASE_URL']}", file=sys.stderr)
except subprocess.TimeoutExpired:
    print("WARNING: Alembic migration timed out", file=sys.stderr)
except Exception as e:
    print(f"WARNING: Failed to apply migrations: {e}", file=sys.stderr)


@pytest.fixture
def db():
    """Provide a database session for tests - uses seeded database (dev or prod) for integrity tests."""
    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
