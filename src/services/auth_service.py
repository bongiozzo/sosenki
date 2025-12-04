"""Authorization service for Mini App endpoints.

Provides unified helpers for:
- Telegram authentication (signature verification, telegram_id extraction)
- User validation and resolution (authenticated, represented, admin-switched)
- Account access authorization (admin override, owner/staff checking)
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.config import bot_config
from src.models.account import Account, AccountType
from src.models.user import User
from src.services.user_service import UserService, UserStatusService

logger = logging.getLogger(__name__)


@dataclass
class AuthorizedUser:
    """Encapsulates authorization context for a request."""

    authenticated_user: User
    """The user who is making the request (from Telegram ID)."""

    target_user: User
    """The user whose data is being accessed (may differ if admin/representation)."""

    is_admin: bool
    """True if authenticated user is an administrator."""

    switched_context: bool
    """True if target_user != authenticated_user (admin switch or representation)."""


def _extract_init_data(
    authorization: str | None,
    x_telegram_init_data: str | None,
    body: dict[str, Any] | None,
) -> str | None:
    """Extract raw init data from multiple transport options.

    Priority:
    1) Authorization: "tma <raw>"
    2) X-Telegram-Init-Data header
    3) JSON body fields: initDataRaw | initData | init_data_raw | init_data

    Args:
        authorization: Authorization header (may contain "tma <raw>")
        x_telegram_init_data: X-Telegram-Init-Data header
        body: Request body (may contain init data fields)

    Returns:
        Raw init data string or None if not found
    """
    # 1) Authorization: tma <raw>
    if authorization:
        auth = authorization.strip()
        if auth.lower().startswith("tma "):
            return auth[4:].strip()

    # 2) Custom header
    if x_telegram_init_data:
        return x_telegram_init_data

    # 3) JSON body (POST)
    if body and isinstance(body, dict):
        for key in ("initDataRaw", "initData", "init_data_raw", "init_data"):
            raw = body.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()

    return None


async def verify_telegram_auth(
    session: AsyncSession,
    authorization: str | None = None,
    x_telegram_init_data: str | None = None,
    body: dict[str, Any] | None = None,
) -> int:
    """Verify Telegram init data signature and extract telegram_id.

    Handles extraction from multiple transport options and validates signature.

    Args:
        session: Database session
        authorization: Authorization header (may contain "tma <raw>")
        x_telegram_init_data: X-Telegram-Init-Data header
        body: Request body (may contain init data fields)

    Returns:
        Verified telegram_id

    Raises:
        HTTPException 401: Missing init data or invalid signature
    """
    # Extract raw init data from supported transports
    raw_init = _extract_init_data(authorization, x_telegram_init_data, body)

    if not raw_init:
        logger.warning("No Telegram init data provided")
        raise HTTPException(status_code=401, detail="NOT_AUTHORIZED")

    # Verify Telegram signature
    parsed_data = UserService.verify_telegram_webapp_signature(
        init_data=raw_init, bot_token=bot_config.telegram_bot_token
    )

    if not parsed_data:
        logger.warning("Invalid Telegram signature")
        raise HTTPException(status_code=401, detail="NOT_AUTHORIZED")

    # Extract user info from parsed data
    user_data = json.loads(parsed_data.get("user", "{}"))
    telegram_id = int(user_data.get("id", 0))

    if not telegram_id:
        raise HTTPException(status_code=401, detail="NOT_AUTHORIZED")

    return telegram_id


async def get_authenticated_user(session: AsyncSession, telegram_id: int) -> User:
    """Get and validate authenticated user.

    Args:
        session: Database session
        telegram_id: Telegram ID to look up

    Returns:
        User object if active and registered

    Raises:
        HTTPException 401: User not found or inactive
    """
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(telegram_id)

    if not user or not user.is_active:
        logger.warning(f"Inactive or unregistered user: telegram_id={telegram_id}")
        raise HTTPException(status_code=401, detail="NOT_AUTHORIZED")

    return user


async def resolve_target_user(
    session: AsyncSession,
    authenticated_user: User,
    selected_user_id: int | None = None,
) -> tuple[User, bool]:
    """Resolve the target user for data access.

    Applies authorization rules:
    1. If admin AND selected_user_id provided → use selected user (context switch)
    2. Else if user has representative_id → use represented user (delegation)
    3. Else → use authenticated user

    Args:
        session: Database session
        authenticated_user: The user making the request
        selected_user_id: User ID selected by admin (for context switching)

    Returns:
        Tuple of (target_user, switched) where switched indicates context change

    Raises:
        HTTPException 404: Selected user not found (admin context switch)
    """
    target_user = authenticated_user
    switched = False

    # Admin override: context switch to selected user
    if selected_user_id is not None and authenticated_user.is_administrator:
        selected_user = await session.get(User, selected_user_id)
        if not selected_user:
            logger.warning(
                f"Admin {authenticated_user.id} requested invalid user_id: {selected_user_id}"
            )
            raise HTTPException(status_code=404, detail="Selected user not found")
        target_user = selected_user
        switched = True
    # Representation fallback: use represented user if no admin context switch
    elif authenticated_user.representative_id:
        user_status_service = UserStatusService(session)
        represented_user = await user_status_service.get_represented_user(authenticated_user.id)
        if represented_user:
            target_user = represented_user
            switched = True

    return target_user, switched


async def authorize_user_context_access(
    session: AsyncSession,
    authenticated_user: User,
    required_role: str | None = None,
    selected_user_id: int | None = None,
) -> AuthorizedUser:
    """Authorize user context access (for /init, /user-context, /properties endpoints).

    Verifies authenticated user is active, optionally checks role, resolves target user,
    and returns unified AuthorizedUser context.

    Args:
        session: Database session
        authenticated_user: The authenticated user making the request
        required_role: Optional role flag to check (e.g., 'is_owner', 'is_administrator')
        selected_user_id: For admins only - user ID to switch to (context switching)

    Returns:
        AuthorizedUser with authenticated and target users

    Raises:
        HTTPException 401: Insufficient permissions or role not met
        HTTPException 404: Selected user not found (admin context switch)
    """
    # Check required role if specified
    if required_role == "is_owner" and not authenticated_user.is_owner:
        logger.warning(f"Non-owner attempted restricted access: user_id={authenticated_user.id}")
        raise HTTPException(status_code=401, detail="NOT_AUTHORIZED")

    if required_role == "is_administrator" and not authenticated_user.is_administrator:
        logger.warning(f"Non-admin attempted restricted access: user_id={authenticated_user.id}")
        raise HTTPException(status_code=401, detail="NOT_AUTHORIZED")

    # Resolve target user (context switching or representation)
    target_user, switched = await resolve_target_user(session, authenticated_user, selected_user_id)

    return AuthorizedUser(
        authenticated_user=authenticated_user,
        target_user=target_user,
        is_admin=authenticated_user.is_administrator,
        switched_context=switched,
    )


async def authorize_account_access(
    session: AsyncSession,
    authenticated_user: User,
    account_id: int,
) -> Account:
    """Authorize account data access (for /transactions, /bills, /account endpoints).

    Verifies:
    1. Account exists
    2. User is admin or staff, OR
    3. Account belongs to user (OWNER/STAFF), OR
    4. Account is ORGANIZATION and user is OWNER, OR
    5. User represents the account owner (authenticated_user.representative_id == account.user_id)

    Args:
        session: Database session
        authenticated_user: The authenticated user making the request
        account_id: Account to access

    Returns:
        Account object if authorized

    Raises:
        HTTPException 400: Invalid account_id
        HTTPException 401: User not authorized to access account
        HTTPException 404: Account not found
    """
    # Validate account_id
    if not account_id or account_id <= 0:
        raise HTTPException(status_code=400, detail="Valid account_id required")

    # Fetch account
    stmt = select(Account).where(Account.id == account_id)
    result = await session.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Authorization: Admin and Staff can access any account
    if authenticated_user.is_administrator or authenticated_user.is_staff:
        return account

    # Authorization: User can access their own personal account (OWNER/STAFF)
    if account.user_id == authenticated_user.id:
        return account

    # Authorization: Owner can access ORGANIZATION or STAFF accounts (shared funds)
    if (
        account.account_type in (AccountType.ORGANIZATION, AccountType.STAFF)
        and authenticated_user.is_owner
    ):
        return account

    # Authorization: Representative can access the account of the user they represent
    # If authenticated_user.representative_id == account.user_id, then authenticated user represents the account owner
    if account.user_id and authenticated_user.representative_id == account.user_id:
        return account

    # Authorization failed
    logger.warning(
        f"User {authenticated_user.id} attempted unauthorized access to account {account_id}"
    )
    raise HTTPException(status_code=401, detail="NOT_AUTHORIZED")


async def authorize_account_access_for_roles(
    session: AsyncSession,
    authenticated_user: User,
    account_id: int,
    allowed_roles: list[str],
) -> Account:
    """Authorize account data access with role restrictions.

    Verifies account exists and user has one of the allowed roles.
    If user is admin, authorization is automatic (admin always allowed).

    Args:
        session: Database session
        authenticated_user: The authenticated user making the request
        account_id: Account to access
        allowed_roles: List of role flags that grant access (e.g., ['is_owner', 'is_administrator', 'is_staff'])

    Returns:
        Account object if authorized

    Raises:
        HTTPException 400: Invalid account_id
        HTTPException 401: User does not have required role or not authorized to access account
        HTTPException 404: Account not found
    """
    # Validate account_id
    if not account_id or account_id <= 0:
        raise HTTPException(status_code=400, detail="Valid account_id required")

    # Fetch account
    stmt = select(Account).where(Account.id == account_id)
    result = await session.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Check role authorization (admin always allowed)
    has_role = any(getattr(authenticated_user, role_flag, False) for role_flag in allowed_roles)

    if not has_role:
        logger.warning(f"User {authenticated_user.id} lacks required role for account access")
        raise HTTPException(status_code=401, detail="NOT_AUTHORIZED")

    return account


__all__ = [
    "AuthorizedUser",
    "verify_telegram_auth",
    "get_authenticated_user",
    "resolve_target_user",
    "authorize_user_context_access",
    "authorize_account_access",
    "authorize_account_access_for_roles",
]
