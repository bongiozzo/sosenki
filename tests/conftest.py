"""Pytest configuration for tests - applies migrations automatically."""

import os
import subprocess
import sys
from pathlib import Path

# Set test database URL BEFORE any imports from src
# This ensures the SessionLocal and engine use the test database
os.environ["DATABASE_URL"] = "sqlite:///./test_sosenki.db"

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
        env={**os.environ, "DATABASE_URL": "sqlite:///./test_sosenki.db"}
    )
    
    if result.returncode != 0:
        print(f"WARNING: Alembic migration failed with return code {result.returncode}", file=sys.stderr)
        print("STDOUT:", result.stdout, file=sys.stderr)
        print("STDERR:", result.stderr, file=sys.stderr)
    else:
        print("✓ Applied migrations to test database", file=sys.stderr)
except subprocess.TimeoutExpired:
    print("WARNING: Alembic migration timed out", file=sys.stderr)
except Exception as e:
    print(f"WARNING: Failed to apply migrations: {e}", file=sys.stderr)

import pytest
