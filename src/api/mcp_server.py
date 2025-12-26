"""MCP Server implementation using FastMCP with HTTP transport for FastAPI integration."""

import json
import logging
from contextlib import asynccontextmanager
from datetime import date
from typing import Any

from fastmcp import FastMCP
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.services.balance_service import BalanceCalculationService
from src.services.locale_service import CURRENCY, format_local_datetime
from src.services.period_service import AsyncServicePeriodService
from src.services.transaction_service import TransactionService
from src.utils.parsers import parse_date

logger = logging.getLogger(__name__)


# ============================================================================
# Database Engine Setup
# ============================================================================


async def _get_database_engine():
    """Create async database engine for MCP operations."""
    import os
    from pathlib import Path

    from sqlalchemy.pool import NullPool

    database_url = os.getenv("DATABASE_URL", "sqlite:///sosenki.dev.db")

    # Convert relative paths to absolute paths for SQLite
    if database_url.startswith("sqlite:///"):
        # Extract the path part
        db_path = database_url.replace("sqlite:///", "")
        # If relative, resolve from project root
        if not db_path.startswith("/"):
            project_root = Path(__file__).parent.parent.parent  # src/api/mcp_server.py -> root
            db_path = str(project_root / db_path)
        # Ensure parent directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        database_url = f"sqlite+aiosqlite:///{db_path}"
    elif database_url.startswith("sqlite://"):
        database_url = database_url.replace("sqlite://", "sqlite+aiosqlite:///")

    engine = create_async_engine(
        database_url,
        echo=False,
        poolclass=NullPool,  # Disable connection pooling for simplicity
    )

    return engine


# ============================================================================
# MCP Lifespan Context Manager
# ============================================================================

_engine = None
_session_maker = None


@asynccontextmanager
async def mcp_lifespan(_app: Any = None):
    """Manage MCP database connection lifecycle.

    Args:
        _app: The FastMCP app instance (required by lifespan protocol)

    Yields an async session maker for database operations.
    Ensures proper cleanup on shutdown.
    """
    global _engine, _session_maker

    logger.info("MCP lifespan starting...")

    # Setup
    try:
        _engine = await _get_database_engine()
        _session_maker = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
        logger.info("✓ MCP database engine initialized")
    except Exception as e:
        logger.error(f"Failed to initialize MCP database: {e}", exc_info=True)
        raise

    try:
        yield
    finally:
        # Cleanup
        try:
            if _engine:
                await _engine.dispose()
                logger.info("✓ MCP database engine disposed")
        except Exception as e:
            logger.error(f"Error disposing MCP database engine: {e}", exc_info=True)


# ============================================================================
# FastMCP Server with Tools
# ============================================================================

mcp = FastMCP("SOSenki", lifespan=mcp_lifespan)


@mcp.tool
async def get_balance(user_id: int) -> str:
    """Get current account balance for a user.

    Args:
        user_id: The user's ID

    Returns:
        JSON string with balance information including:
        - balance: Current account balance in base currency
        - currency: Currency code (USD, EUR, etc.)
        - last_updated: ISO timestamp of last balance update
    """
    if not _session_maker:
        return json.dumps({"error": "Database not initialized"})

    try:
        async with _session_maker() as session:
            service = BalanceCalculationService(session)

            # Validate user exists
            user = await service.get_user_by_id(user_id)
            if not user:
                return json.dumps({"error": f"User {user_id} not found"})

            # Get account
            account = await service.get_account_for_user(user_id)
            if not account:
                return json.dumps({"error": f"No account found for user {user_id}"})

            # Calculate balance
            balance = await service.calculate_user_balance(user_id)

            return json.dumps(
                {
                    "user_id": user_id,
                    "account_id": account.id,
                    "balance": float(balance),
                    "currency": CURRENCY,
                    "last_updated": (
                        format_local_datetime(account.updated_at) if account.updated_at else None
                    ),
                }
            )
    except Exception as e:
        logger.error(f"Error in get_balance: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool
async def list_bills(user_id: int, limit: int = 10) -> str:
    """List recent bills for a user.

    Args:
        user_id: The user's ID
        limit: Maximum number of bills to return (default: 10)

    Returns:
        JSON string with list of bills containing:
        - bill_id: Bill identifier
        - amount: Bill amount
        - bill_date: Date bill was issued
        - bill_type: Type of bill
        - status: PAID, PENDING, or OVERDUE
    """
    if not _session_maker:
        return json.dumps({"error": "Database not initialized"})

    try:
        async with _session_maker() as session:
            service = BalanceCalculationService(session)

            # Get account to verify user exists
            account = await service.get_account_for_user(user_id)
            if not account:
                return json.dumps({"error": f"No account found for user {user_id}"})

            # Get bills using service
            bills = await service.list_bills_for_user(user_id, limit)

            return json.dumps(
                {
                    "user_id": user_id,
                    "account_id": account.id,
                    "currency": CURRENCY,
                    "bills": [
                        {
                            "bill_id": bill.bill_id,
                            "amount": bill.amount,
                            "bill_date": bill.bill_date,
                            "bill_type": bill.bill_type,
                            "status": "PENDING",  # TODO: Implement status logic
                        }
                        for bill in bills
                    ],
                }
            )
    except Exception as e:
        logger.error(f"Error in list_bills: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool
async def get_period_info(period_id: int) -> str:
    """Get service period information.

    Args:
        period_id: The service period ID

    Returns:
        JSON string with period details including:
        - period_id: Period identifier
        - name: Period name
        - start_date: Period start date
        - end_date: Period end date
        - active: Whether period is currently active
    """
    if not _session_maker:
        return json.dumps({"error": "Database not initialized"})

    try:
        async with _session_maker() as session:
            service = AsyncServicePeriodService(session)
            period_info = await service.get_period_info(period_id)

            if not period_info:
                return json.dumps({"error": f"Period {period_id} not found"})

            return json.dumps(
                {
                    "period_id": period_info.period_id,
                    "name": period_info.name,
                    "start_date": period_info.start_date,
                    "end_date": period_info.end_date,
                    "active": period_info.is_active,
                }
            )
    except Exception as e:
        logger.error(f"Error in get_period_info: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool
async def create_service_period(
    name: str,
    start_date: str,
    end_date: str,
    electricity_start: int | None = None,
    electricity_rate: float | None = None,
) -> str:
    """Create a new service period.

    Admin-only tool. Requires authentication.

    Args:
        name: Period name (e.g., "September 2025 - January 2026")
        start_date: Period start date in ISO format (YYYY-MM-DD)
        end_date: Period end date in ISO format (YYYY-MM-DD)
        electricity_start: Optional starting electricity meter reading
        electricity_rate: Optional electricity rate per unit

    Returns:
        JSON string with created period details or error message.
        On success, includes period_id, name, start_date, end_date.
        On error, includes error message and validation details.
    """
    if not _session_maker:
        return json.dumps({"error": "Database not initialized"})

    # Parse and validate dates
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError as e:
        return json.dumps({"error": f"Invalid date format: {e}. Use YYYY-MM-DD."})

    try:
        async with _session_maker() as session:
            service = AsyncServicePeriodService(session)
            new_period = await service.create_period(start, end, name)

            return json.dumps(
                {
                    "success": True,
                    "period_id": new_period.id,
                    "name": new_period.name,
                    "start_date": new_period.start_date.isoformat(),
                    "end_date": new_period.end_date.isoformat(),
                }
            )
    except ValueError as e:
        # Date validation error from service
        return json.dumps(
            {
                "error": str(e),
                "start_date": start_date,
                "end_date": end_date,
            }
        )
    except Exception as e:
        logger.error(f"Error in create_service_period: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


def _parse_tool_transaction_date(value: str | None) -> date | None:
    """Parse a transaction date string supporting DD.MM.YYYY and YYYY-MM-DD."""
    if not value:
        return None

    cleaned = value.strip()
    if not cleaned:
        return None

    try:
        parsed = parse_date(cleaned)
        if parsed:
            return parsed
    except ValueError:
        pass

    try:
        return date.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValueError("Invalid transaction_date format. Use DD.MM.YYYY or YYYY-MM-DD.") from exc


@mcp.tool
async def create_transaction(
    from_account_id: int,
    to_account_id: int,
    amount: float,
    description: str,
    transaction_date: str | None = None,
) -> str:
    """Create a new transaction between accounts.

    Admin-only tool. Creates a transaction from one account to another
    with auto-generated description and audit logging.

    Args:
        from_account_id: Source account ID
        to_account_id: Destination account ID
        amount: Transaction amount (must be positive)
        description: Transaction description
        transaction_date: Optional transaction date (DD.MM.YYYY or YYYY-MM-DD)

    Returns:
        JSON string with created transaction details or error message.
        On success, includes transaction_id, from_account, to_account, amount, date.
        On error, includes error message and validation details.
    """
    if not _session_maker:
        return json.dumps({"error": "Database not initialized"})

    # Validate amount
    if amount <= 0:
        return json.dumps({"error": "Amount must be positive"})

    try:
        async with _session_maker() as session:
            service = TransactionService(session)

            # Validate accounts exist
            from_account = await service.get_account_by_id(from_account_id)
            if not from_account:
                return json.dumps({"error": f"From account {from_account_id} not found"})

            to_account = await service.get_account_by_id(to_account_id)
            if not to_account:
                return json.dumps({"error": f"To account {to_account_id} not found"})

            # Create transaction
            from decimal import Decimal

            parsed_transaction_date = None
            if transaction_date:
                try:
                    parsed_transaction_date = _parse_tool_transaction_date(transaction_date)
                except ValueError as exc:  # pragma: no cover - validation path
                    return json.dumps({"error": str(exc)})

            transaction = await service.create_transaction(
                from_account_id=from_account_id,
                to_account_id=to_account_id,
                amount=Decimal(str(amount)),
                description=description,
                transaction_date=parsed_transaction_date,
            )

            await session.commit()

            return json.dumps(
                {
                    "success": True,
                    "transaction_id": transaction.id,
                    "from_account_id": from_account.id,
                    "from_account_name": from_account.name,
                    "to_account_id": to_account.id,
                    "to_account_name": to_account.name,
                    "amount": float(transaction.amount),
                    "description": transaction.description,
                    "transaction_date": transaction.transaction_date.isoformat(),
                    "currency": CURRENCY,
                }
            )
    except ValueError as e:
        # Validation error from service
        return json.dumps({"error": str(e)})
    except Exception as e:
        logger.error(f"Error in create_transaction: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


# ============================================================================
# HTTP App for FastAPI Integration
# ============================================================================

# FastMCP provides http_app() for mounting in FastAPI
# path="/" ensures endpoint is at mount root, not /mcp/mcp
# The .lifespan property handles lifecycle (invokes mcp_lifespan automatically)
mcp_http_app = mcp.http_app(path="/")


__all__ = ["mcp", "mcp_http_app"]
