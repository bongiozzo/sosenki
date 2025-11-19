"""Mini App API endpoints."""

import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.config import bot_config
from src.models.account import Account
from src.models.transaction import Transaction
from src.services import get_async_session
from src.services.user_service import UserService, UserStatusService

logger = logging.getLogger(__name__)

# Create router for Mini App endpoints
router = APIRouter(prefix="/api/mini-app", tags=["mini-app"])


# Helpers
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


# Response schemas
class UserStatusResponse(BaseModel):
    """Response schema for user status endpoint."""

    user_id: int
    roles: list[str]  # e.g., ["investor", "owner", "stakeholder"]
    stakeholder_url: str | None  # URL from environment, may be null
    share_percentage: int | None  # 1 (signed), 0 (unsigned owner), None (non-owner)
    representative_of: dict[str, int | str | None] | None = None  # User being represented, if any
    represented_user_roles: list[str] | None = (
        None  # Roles of represented user if representing someone
    )
    represented_user_share_percentage: int | None = (
        None  # Share percentage of represented user if representing someone
    )

    model_config = ConfigDict(from_attributes=True)


class PropertyResponse(BaseModel):
    """Response schema for a single property."""

    id: int
    property_name: str
    type: str
    share_weight: str | None  # Formatted decimal as string for display
    is_ready: bool
    is_for_tenant: bool
    photo_link: str | None
    sale_price: str | None  # Formatted decimal as string for display
    main_property_id: int | None  # ID of parent property if this is an additional property

    model_config = ConfigDict(from_attributes=True)


class PropertyListResponse(BaseModel):
    """Response schema for properties list endpoint."""

    properties: list[PropertyResponse]
    total_count: int

    model_config = ConfigDict(from_attributes=True)


@router.post("/config")
async def get_config(
    authorization: str | None = Header(None, alias="Authorization"),  # noqa: B008
    body: dict[str, Any] | None = Body(None),  # noqa: B008
) -> dict[str, Any]:
    """
    Get Mini App configuration from environment variables.

    Returns public configuration values like photo gallery URL.

    Args:
        authorization: Authorization header with Telegram initData ("tma <raw>").
        body: Optional JSON body with initData if not in header.

    Returns:
        {"photoGalleryUrl": str | null}
    """
    # Extract initData (signature verification not strictly needed for config, but maintains consistency)
    init_data_raw = _extract_init_data(authorization, None, body)
    if not init_data_raw:
        raise HTTPException(status_code=401, detail="Missing init data")

    try:
        photo_gallery_url = os.getenv("PHOTO_GALLERY_URL")
        return {"photoGalleryUrl": photo_gallery_url}
    except Exception as e:
        logger.error(f"Error in /api/mini-app/config: {e}", exc_info=True)
        return {"photoGalleryUrl": None}


@router.post("/init")
async def mini_app_init(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    authorization: str | None = Header(None, alias="Authorization"),  # noqa: B008
    body: dict[str, Any] | None = Body(None),  # noqa: B008
) -> dict[str, Any]:
    """
    Initialize Mini App and verify user registration status.

    Returns user access status and menu configuration for registered users,
    or access denied message for non-registered users.

    Args:
        session: Database session

    Returns:
        For registered users: {"isRegistered": true, "menu": [...], "userName": ...}
        For non-registered: {"isRegistered": false, "message": "Access is limited", ...}

    Raises:
        401: Invalid Telegram signature
        500: Server error
    """
    try:
        # Extract raw init data from supported transports
        raw_init = _extract_init_data(authorization, None, body)

        if not raw_init:
            logger.warning("No Telegram init data provided")
            raise HTTPException(status_code=401, detail="Missing Telegram init data")

        # Verify Telegram signature
        parsed_data = UserService.verify_telegram_webapp_signature(
            init_data=raw_init, bot_token=bot_config.telegram_bot_token
        )

        if not parsed_data:
            logger.warning("Invalid Telegram signature in /api/mini-app/init")
            raise HTTPException(status_code=401, detail="Invalid Telegram signature")

        # Extract user info from parsed data
        user_data = json.loads(parsed_data.get("user", "{}"))
        telegram_id = str(user_data.get("id"))
        username = user_data.get("username")
        first_name = user_data.get("first_name")

        if not telegram_id:
            raise HTTPException(status_code=401, detail="User ID not found in init data")

        # Check user registration status
        user_service = UserService(session)
        user = await user_service.get_by_telegram_id(telegram_id)

        # Check if user can access Mini App (is_active=True)
        if user and user.is_active:
            # Registered user - return menu
            menu = [
                {"id": "rule", "label": "Rule", "enabled": True},
                {"id": "pay", "label": "Pay", "enabled": True},
                {"id": "invest", "label": "Invest", "enabled": user.is_investor},
            ]

            return {
                "isRegistered": True,
                "userId": telegram_id,
                "userName": username or first_name or "User",
                "firstName": first_name,
                "isInvestor": user.is_investor,
                "menu": menu,
            }
        else:
            # Non-registered user - return access denied
            return {
                "isRegistered": False,
                "userId": telegram_id,
                "message": "Access is limited",
                "instruction": "Send /request to bot to request access",
                "menu": [],
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/mini-app/init: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server error") from e


@router.post("/verify-registration")
async def verify_registration(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    authorization: str | None = Header(None, alias="Authorization"),  # noqa: B008
    body: dict[str, Any] | None = Body(None),  # noqa: B008
) -> dict[str, Any]:
    """
    Verify user registration status (explicit refresh).

    Similar to /init but provides just registration status without menu.
    Useful for explicit refresh after user requests it.

    Args:
        session: Database session

    Returns:
        {"isRegistered": bool, "userId": str, ...}

    Raises:
        401: Invalid Telegram signature
    """
    try:
        # Extract raw init data
        raw_init = _extract_init_data(authorization, None, body)

        # Verify signature
        parsed_data = UserService.verify_telegram_webapp_signature(
            init_data=raw_init or "", bot_token=bot_config.telegram_bot_token
        )

        if not parsed_data:
            raise HTTPException(status_code=401, detail="Invalid Telegram signature")

        # Extract user info
        user_data = json.loads(parsed_data.get("user", "{}"))
        telegram_id = str(user_data.get("id"))
        username = user_data.get("username")

        if not telegram_id:
            raise HTTPException(status_code=401, detail="User ID not found")

        # Check registration
        user_service = UserService(session)
        user = await user_service.get_by_telegram_id(telegram_id)

        if user and user.is_active:
            return {
                "isRegistered": True,
                "userId": telegram_id,
                "userName": username,
                "isActive": user.is_active,
                "isInvestor": user.is_investor,
            }
        else:
            return {
                "isRegistered": False,
                "userId": telegram_id,
                "message": "Your access request is pending or was not approved",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/mini-app/verify-registration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server error") from e


@router.post("/menu-action")
async def parse_action(
    authorization: str | None = Header(None, alias="Authorization"),  # noqa: B008
    x_telegram_init_data: str | None = Header(None, alias="X-Telegram-Init-Data"),  # noqa: B008
    action_data: dict[str, Any] | None = Body(None),  # noqa: B008
) -> dict[str, Any]:
    """
    Handle menu action (placeholder for future features).

    Args:
        Telegram WebApp initData (via Authorization/X-Header or body)
        action_data: Action data (e.g., {"action": "rule", "data": {}})

    Returns:
        {"success": bool, "message": str}

    Raises:
        401: Invalid signature or not registered
        403: Access denied
    """
    try:
        # Extract raw init data and verify signature
        raw_init = _extract_init_data(authorization, x_telegram_init_data, action_data)
        parsed_data = UserService.verify_telegram_webapp_signature(
            init_data=raw_init or "", bot_token=bot_config.telegram_bot_token
        )

        if not parsed_data:
            raise HTTPException(status_code=401, detail="Invalid Telegram signature")

        # Placeholder response - features not implemented yet
        return {"success": True, "message": "Feature coming soon!", "redirectUrl": None}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/mini-app/menu-action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server error") from e


@router.post("/user-status", response_model=UserStatusResponse)
async def get_user_status(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    authorization: str | None = Header(None, alias="Authorization"),  # noqa: B008
    body: dict[str, Any] | None = Body(None),  # noqa: B008
) -> UserStatusResponse:
    """
    Get current user's status information for dashboard display.

    Returns user's active roles, stakeholder contract status (for owners),
    and stakeholder shares link (for owners only).

    Args:
        session: Database session

    Returns:
        UserStatusResponse with user_id, roles, stakeholder_url, share_percentage

    Raises:
        401: Invalid Telegram signature
        403: User not registered or inactive
        500: Server error
    """
    try:
        # Extract and verify Telegram signature
        raw_init = _extract_init_data(authorization, None, body)
        parsed_data = UserService.verify_telegram_webapp_signature(
            init_data=raw_init or "", bot_token=bot_config.telegram_bot_token
        )

        if not parsed_data:
            logger.warning("Invalid Telegram signature in /api/mini-app/user-status")
            raise HTTPException(status_code=401, detail="Invalid Telegram signature")

        # Extract telegram_id from parsed data
        user_data = json.loads(parsed_data.get("user", "{}"))
        telegram_id = str(user_data.get("id"))

        if not telegram_id:
            raise HTTPException(status_code=401, detail="No user ID in init data")

        # Get user from database
        user_service = UserService(session)
        user = await user_service.get_by_telegram_id(telegram_id)

        if not user or not user.is_active:
            logger.warning(f"Unauthorized access attempt: telegram_id={telegram_id}")
            raise HTTPException(status_code=403, detail="User not registered or inactive")

        # Get active roles
        roles = UserStatusService.get_active_roles(user)

        # Get stakeholder URL from environment (for owners only)
        import os

        stakeholder_url = None
        if user.is_owner:
            stakeholder_url = os.getenv("STAKEHOLDER_SHARES_URL")

        # Get share percentage (for owners only)
        share_percentage = UserStatusService.get_share_percentage(user)

        # Get representative info (if user represents someone)
        representative_of = None
        represented_user_roles = None
        represented_user_share_percentage = None

        if user.representative_id:
            user_status_service = UserStatusService(session)
            represented_user = await user_status_service.get_represented_user(user.id)
            if represented_user:
                representative_of = {
                    "user_id": represented_user.id,
                    "name": represented_user.name,
                    "telegram_id": represented_user.telegram_id,
                }
                # Get represented user's roles and share percentage for context switching
                represented_user_roles = UserStatusService.get_active_roles(represented_user)
                represented_user_share_percentage = UserStatusService.get_share_percentage(
                    represented_user
                )

        return UserStatusResponse(
            user_id=user.id,
            roles=roles,
            stakeholder_url=stakeholder_url,
            share_percentage=share_percentage,
            representative_of=representative_of,
            represented_user_roles=represented_user_roles,
            represented_user_share_percentage=represented_user_share_percentage,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/mini-app/user-status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server error") from e


@router.post("/properties")
async def get_properties(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    authorization: str | None = Header(None, alias="Authorization"),  # noqa: B008
    body: dict[str, Any] | None = Body(None),  # noqa: B008
) -> PropertyListResponse:
    """
    Get properties for owner or represented owner.

    Returns properties owned by the authenticated user if they are an owner,
    or properties of the user they represent if applicable.
    Uses context switching: if user represents someone, returns their properties.

    Args:
        session: Database session

    Returns:
        PropertyListResponse with list of properties and total count

    Raises:
        401: Invalid Telegram signature
        403: User not registered, inactive, or not an owner
        500: Server error
    """
    try:
        # Extract and verify Telegram signature
        raw_init = _extract_init_data(authorization, None, body)
        parsed_data = UserService.verify_telegram_webapp_signature(
            init_data=raw_init or "", bot_token=bot_config.telegram_bot_token
        )

        if not parsed_data:
            logger.warning("Invalid Telegram signature in /api/mini-app/properties")
            raise HTTPException(status_code=401, detail="Invalid Telegram signature")

        # Extract telegram_id from parsed data
        user_data = json.loads(parsed_data.get("user", "{}"))
        telegram_id = str(user_data.get("id"))

        if not telegram_id:
            raise HTTPException(status_code=401, detail="No user ID in init data")

        # Get user from database
        user_service = UserService(session)
        user = await user_service.get_by_telegram_id(telegram_id)

        if not user or not user.is_active:
            logger.warning(f"Unauthorized access attempt: telegram_id={telegram_id}")
            raise HTTPException(status_code=403, detail="User not registered or inactive")

        # Determine target user for property lookup (context switching)
        target_user_id = user.id
        is_owner = user.is_owner

        # If user represents someone, switch context to represented user
        if user.representative_id:
            user_status_service = UserStatusService(session)
            represented_user = await user_status_service.get_represented_user(user.id)
            if represented_user:
                target_user_id = represented_user.id
                is_owner = represented_user.is_owner

        # Only owners can view properties
        if not is_owner:
            logger.warning(f"Non-owner attempted to access properties: telegram_id={telegram_id}")
            raise HTTPException(status_code=403, detail="Only owners can view properties")

        # Fetch properties for target user (context-switched if representing)
        from src.models.property import Property

        stmt = (
            select(Property)
            .where(
                Property.owner_id == target_user_id,
                Property.is_active == True,  # noqa: E712
            )
            .order_by(Property.id)
        )  # Sort by ID ascending for consistent ordering

        result = await session.execute(stmt)
        properties = result.scalars().all()

        # Format response
        property_responses = []
        for prop in properties:
            property_responses.append(
                PropertyResponse(
                    id=prop.id,
                    property_name=prop.property_name,
                    type=prop.type,
                    share_weight=str(prop.share_weight) if prop.share_weight else None,
                    is_ready=prop.is_ready,
                    is_for_tenant=prop.is_for_tenant,
                    photo_link=prop.photo_link,
                    sale_price=str(prop.sale_price) if prop.sale_price else None,
                    main_property_id=prop.main_property_id,
                )
            )

        return PropertyListResponse(
            properties=property_responses,
            total_count=len(property_responses),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/mini-app/properties: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server error") from e


# Transaction Response Models
class TransactionResponse(BaseModel):
    """Response model for a single transaction."""

    model_config = ConfigDict(from_attributes=True)

    from_ac_name: str
    """Account name the transaction is from."""

    to_ac_name: str
    """Account name the transaction is to."""

    amount: float
    """Transaction amount."""

    date: str
    """Transaction date in ISO format."""

    description: str | None = None
    """Optional transaction description."""


class TransactionListResponse(BaseModel):
    """Response for transactions list."""

    transactions: list[TransactionResponse]


@router.post("/transactions-list")
async def transactions_list(
    scope: str = "all",
    authorization: str | None = Header(None),  # noqa: B008
    x_telegram_init_data: str | None = Header(None),  # noqa: B008
    body: dict[str, Any] | None = Body(None),  # noqa: B008
    db: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> TransactionListResponse:
    """Get list of transactions.

    Args:
        scope: Filter scope - 'personal' returns only user's transactions,
               'all' (default) returns all organization transactions.

    Returns all transactions or user's transactions based on scope parameter.
    """
    # Extract and verify init data
    init_data_raw = _extract_init_data(authorization, x_telegram_init_data, body)
    parsed_data = UserService.verify_telegram_webapp_signature(
        init_data=init_data_raw or "", bot_token=bot_config.telegram_bot_token
    )

    if not parsed_data:
        logger.warning("Invalid Telegram signature in /api/mini-app/transactions-list")
        raise HTTPException(status_code=401, detail="Invalid Telegram signature")

    # Extract telegram_id from parsed data
    user_data = json.loads(parsed_data.get("user", "{}"))
    telegram_id = str(user_data.get("id"))

    if not telegram_id:
        raise HTTPException(status_code=401, detail="No user ID in init data")

    try:
        # Get user from database
        user_service = UserService(db)
        user = await user_service.get_by_telegram_id(telegram_id)

        if not user or not user.is_active:
            logger.warning(f"Unauthorized access attempt: telegram_id={telegram_id}")
            raise HTTPException(status_code=403, detail="User not registered or inactive")

        user_id = user.id

        # Get user's accounts for personal scope filtering
        user_accounts_stmt = select(Account).where(Account.user_id == user_id)
        result = await db.execute(user_accounts_stmt)
        user_accounts = result.scalars().all()
        account_ids = [acc.id for acc in user_accounts]

        if not account_ids and scope == "personal":
            # No transactions if user has no accounts
            return TransactionListResponse(transactions=[])

        # Get all transactions involving user's accounts
        # Use separate joins for from and to accounts
        from_account_alias = (
            select(Account.name.label("from_ac_name"))
            .where(Account.id == Transaction.from_account_id)
            .correlate(Transaction)
            .scalar_subquery()
        )

        to_account_alias = (
            select(Account.name.label("to_ac_name"))
            .where(Account.id == Transaction.to_account_id)
            .correlate(Transaction)
            .scalar_subquery()
        )

        # Build WHERE clause based on scope
        where_clause = []
        if scope == "personal" and account_ids:
            where_clause = [
                (Transaction.from_account_id.in_(account_ids))
                | (Transaction.to_account_id.in_(account_ids))
            ]

        trans_stmt = select(
            from_account_alias.label("from_ac_name"),
            to_account_alias.label("to_ac_name"),
            Transaction.amount,
            Transaction.transaction_date,
            Transaction.description,
        ).order_by(Transaction.transaction_date.desc())

        if where_clause:
            trans_stmt = trans_stmt.where(*where_clause)

        result = await db.execute(trans_stmt)
        transactions_data = result.all()

        transactions_list_data = [
            TransactionResponse(
                from_ac_name=row[0] or "Unknown",
                to_ac_name=row[1] or "Unknown",
                amount=float(row[2]),
                date=row[3].isoformat() if row[3] else "",
                description=row[4],
            )
            for row in transactions_data
        ]

        return TransactionListResponse(transactions=transactions_list_data)

    except Exception as e:
        logger.error(f"Error in /api/mini-app/transactions-list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server error") from e


# Endpoints will be implemented in Phase 5 and Polish
# - GET /api/mini-app/verify-registration
# - POST /api/mini-app/menu-action


__all__ = ["router"]
