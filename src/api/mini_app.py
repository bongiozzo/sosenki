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
from src.models.user import User
from src.services import get_async_session
from src.services.localizer import get_translations
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


async def _resolve_target_user(
    session: AsyncSession,
    telegram_id: str,
    representing: bool | None = None,
    selected_user_id: int | None = None,
) -> tuple[User, bool]:
    """
    Resolve the target user (authenticated vs represented) for dataset endpoints.

    Args:
        session: Database session
        telegram_id: Telegram ID of the authenticated user
        representing: Whether to consider representation (legacy parameter)
        selected_user_id: User ID selected by admin (takes precedence if admin)

    Returns:
        Tuple of (target_user, switched) where switched indicates context change
    """
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(telegram_id)

    if not user or not user.is_active:
        logger.warning(f"Unauthorized access attempt: telegram_id={telegram_id}")
        raise HTTPException(status_code=403, detail="User not registered or inactive")

    target_user = user
    switched = False

    # Admin override: if selected_user_id provided and user is admin, use selected user
    if selected_user_id is not None and user.is_administrator:
        selected_user = await session.get(User, selected_user_id)
        if selected_user:
            target_user = selected_user
            switched = True
        else:
            logger.warning(f"Admin {telegram_id} requested invalid user_id: {selected_user_id}")
            raise HTTPException(status_code=404, detail="Selected user not found")
    else:
        # Fallback to legacy representation logic (only if no admin selection)
        consider_represented = representing is True or (
            representing is None and user.representative_id is not None
        )

        if consider_represented and user.representative_id:
            user_status_service = UserStatusService(session)
            represented_user = await user_status_service.get_represented_user(user.id)
            if represented_user:
                target_user = represented_user
                switched = True

    return target_user, switched


# Response schemas
class UserStatusResponse(BaseModel):
    """Response schema for user status endpoint."""

    user_id: int
    account_id: int  # Account ID for the authenticated or represented user
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


class UserListItemResponse(BaseModel):
    """Response schema for a single user in the users list."""

    user_id: int
    name: str
    telegram_id: str | None

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Response schema for users list endpoint."""

    users: list[UserListItemResponse]

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


@router.get("/translations")
async def get_translations_endpoint() -> dict[str, Any]:
    """
    Get all translations for the Mini App.

    Returns the full translations dictionary (mini_app section only).
    Public endpoint - no authentication required.

    Returns:
        Translations dictionary for mini_app namespace.
    """
    translations = get_translations()
    return translations.get("mini_app", {})


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
    selected_user_id: int | None = None,  # noqa: B008
) -> UserStatusResponse:
    """
    Get current user's status information for dashboard display.

    Returns user's active roles, stakeholder contract status (for owners),
    and stakeholder shares link (for owners only).

    Args:
        session: Database session
        selected_user_id: User ID selected by admin (takes precedence if admin)

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

        # Resolve target user (authenticated or admin-selected)
        target_user, _ = await _resolve_target_user(session, telegram_id, None, selected_user_id)

        # Get active roles
        roles = UserStatusService.get_active_roles(target_user)

        # Get stakeholder URL from environment (for owners only)
        import os

        stakeholder_url = None
        if target_user.is_owner:
            stakeholder_url = os.getenv("STAKEHOLDER_SHARES_URL")

        # Get share percentage (for owners only)
        share_percentage = UserStatusService.get_share_percentage(target_user)

        # Get representative info (if user represents someone) - only for authenticated user, not selected user
        representative_of = None
        represented_user_roles = None
        represented_user_share_percentage = None

        # Check if authenticated user (not target) represents someone
        user_service = UserService(session)
        auth_user = await user_service.get_by_telegram_id(telegram_id)
        if auth_user and auth_user.representative_id:
            user_status_service = UserStatusService(session)
            represented_user = await user_status_service.get_represented_user(auth_user.id)
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

        # Get target user's account ID
        account_stmt = select(Account).where(Account.user_id == target_user.id)
        account_result = await session.execute(account_stmt)
        target_account = account_result.scalar_one_or_none()
        account_id = target_account.id if target_account else None

        if not account_id:
            raise HTTPException(status_code=500, detail="Account not found for user")

        return UserStatusResponse(
            user_id=target_user.id,
            account_id=account_id,
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


@router.post("/users", response_model=UserListResponse)
async def get_users(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    authorization: str | None = Header(None, alias="Authorization"),  # noqa: B008
    body: dict[str, Any] | None = Body(None),  # noqa: B008
) -> UserListResponse:
    """
    Get list of all users for admin dropdown (administrators only).

    Returns all users ordered by name. Access restricted to administrators.

    Args:
        session: Database session

    Returns:
        UserListResponse with list of all users

    Raises:
        401: Invalid Telegram signature
        403: User not registered, inactive, or not an administrator
        500: Server error
    """
    try:
        # Extract and verify Telegram signature
        raw_init = _extract_init_data(authorization, None, body)
        parsed_data = UserService.verify_telegram_webapp_signature(
            init_data=raw_init or "", bot_token=bot_config.telegram_bot_token
        )

        if not parsed_data:
            logger.warning("Invalid Telegram signature in /api/mini-app/users")
            raise HTTPException(status_code=401, detail="Invalid Telegram signature")

        # Extract telegram_id from parsed data
        user_data = json.loads(parsed_data.get("user", "{}"))
        telegram_id = str(user_data.get("id"))

        if not telegram_id:
            raise HTTPException(status_code=401, detail="No user ID in init data")

        # Check if user is administrator
        user_service = UserService(session)
        is_admin = await user_service.is_administrator(telegram_id)

        if not is_admin:
            logger.warning(f"Non-admin attempted to access users list: telegram_id={telegram_id}")
            raise HTTPException(status_code=403, detail="Only administrators can view users list")

        # Fetch all users ordered by name
        all_users = await user_service.get_all_users()

        # Format response
        user_list = [
            UserListItemResponse(
                user_id=u.id,
                name=u.name,
                telegram_id=u.telegram_id,
            )
            for u in all_users
        ]

        return UserListResponse(users=user_list)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/mini-app/users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server error") from e


@router.post("/properties")
async def get_properties(
    representing: bool | None = None,
    selected_user_id: int | None = None,
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

        user_data = json.loads(parsed_data.get("user", "{}"))
        telegram_id = str(user_data.get("id"))

        if not telegram_id:
            raise HTTPException(status_code=401, detail="No user ID in init data")

        target_user, _ = await _resolve_target_user(
            session, telegram_id, representing, selected_user_id
        )

        if not target_user.is_owner:
            logger.warning(f"Non-owner attempted to access properties: telegram_id={telegram_id}")
            raise HTTPException(status_code=403, detail="Only owners can view properties")

        # Fetch properties for target user (context-switched if representing)
        from src.models.property import Property

        stmt = (
            select(Property)
            .where(
                Property.owner_id == target_user.id,
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


# Helper functions for bills endpoint
def _build_electricity_reading_subqueries(
    reading_date_comparison: str,
) -> tuple:
    """Build start and end reading subqueries for electricity bills.

    Args:
        reading_date_comparison: Either "start" or "end" to build appropriate query

    Returns:
        Tuple of (start_reading_alias, end_reading_alias) scalar subqueries
    """
    from src.models.bill import Bill
    from src.models.electricity_reading import ElectricityReading
    from src.models.service_period import ServicePeriod

    start_reading_alias = (
        select(ElectricityReading.reading_value)
        .join(Account, Account.user_id == ElectricityReading.user_id)
        .where(
            (Account.id == Bill.account_id)
            & (ElectricityReading.property_id == Bill.property_id)
            & (ElectricityReading.reading_date <= ServicePeriod.start_date)
        )
        .order_by(ElectricityReading.reading_date.desc())
        .limit(1)
        .correlate(Bill, ServicePeriod)
        .scalar_subquery()
    )

    end_reading_alias = (
        select(ElectricityReading.reading_value)
        .join(Account, Account.user_id == ElectricityReading.user_id)
        .where(
            (Account.id == Bill.account_id)
            & (ElectricityReading.property_id == Bill.property_id)
            & (ElectricityReading.reading_date <= ServicePeriod.end_date)
        )
        .order_by(ElectricityReading.reading_date.desc())
        .limit(1)
        .correlate(Bill, ServicePeriod)
        .scalar_subquery()
    )

    return start_reading_alias, end_reading_alias


def _format_bill_response(bill, service_period, property_obj, start_reading, end_reading) -> dict:
    """Format bill data into response dict.

    Args:
        bill: Bill model instance
        service_period: ServicePeriod model instance
        property_obj: Property model instance or None
        start_reading: Start meter reading value or None
        end_reading: End meter reading value or None

    Returns:
        Formatted bill response dictionary
    """
    consumption = None
    if start_reading is not None and end_reading is not None and end_reading >= start_reading:
        consumption = end_reading - start_reading

    return {
        "period_name": service_period.name,
        "period_start_date": service_period.start_date.isoformat(),
        "period_end_date": service_period.end_date.isoformat(),
        "property_name": property_obj.property_name if property_obj else None,
        "property_type": property_obj.type if property_obj else None,
        "comment": bill.comment,
        "bill_amount": float(bill.bill_amount),
        "bill_type": bill.bill_type.value,
        "start_reading": start_reading,
        "end_reading": end_reading,
        "consumption": consumption,
    }


# Transaction Response Models
class TransactionResponse(BaseModel):
    """Response model for a single transaction."""

    model_config = ConfigDict(from_attributes=True)

    from_account_id: int
    """Account ID the transaction is from."""

    from_ac_name: str
    """Account name the transaction is from."""

    to_account_id: int
    """Account ID the transaction is to."""

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


class ElectricityBillResponse(BaseModel):
    """Response schema for a single electricity bill."""

    period_name: str
    """Service period name (e.g., '2024-Q4')."""

    period_start_date: str
    """Period start date in ISO format."""

    period_end_date: str
    """Period end date in ISO format."""

    property_name: str | None = None
    """Property name if bill is for a property."""

    property_type: str | None = None
    """Property type if bill is for a property."""

    start_reading: float | None = None
    """Meter reading at period start (electricity bills only)."""

    end_reading: float | None = None
    """Meter reading at period end (electricity bills only)."""

    consumption: float | None = None
    """Electricity consumption (end - start) (electricity bills only)."""

    bill_amount: float
    """Bill amount in rubles."""

    bill_type: str | None = None
    """Bill type: electricity, shared_electricity, conservation, main."""

    comment: str | None = None
    """Optional comment (e.g., property name when property not found)."""

    model_config = ConfigDict(from_attributes=True)


class BillsListResponse(BaseModel):
    """Response for bills list (all bill types: electricity, shared electricity, conservation, main)."""

    bills: list[ElectricityBillResponse]


@router.post("/transactions-list")
async def transactions_list(
    account_id: int,
    scope: str = "all",
    authorization: str | None = Header(None),  # noqa: B008
    x_telegram_init_data: str | None = Header(None),  # noqa: B008
    body: dict[str, Any] | None = Body(None),  # noqa: B008
    db: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> TransactionListResponse:
    """Get list of transactions for a specific account.

    Args:
        account_id: Account ID to fetch transactions for (required, extracted during page initialization).
        scope: Filter scope - 'personal' returns only account's transactions,
               'all' (default) returns all organization transactions visible to account.

    Returns all transactions or account's transactions based on scope parameter.
    """
    # Validate account_id
    if not account_id or account_id <= 0:
        raise HTTPException(status_code=400, detail="Valid account_id required")

    # Extract and verify init data (for authentication only)
    init_data_raw = _extract_init_data(authorization, x_telegram_init_data, body)
    parsed_data = UserService.verify_telegram_webapp_signature(
        init_data=init_data_raw or "", bot_token=bot_config.telegram_bot_token
    )

    if not parsed_data:
        logger.warning("Invalid Telegram signature in /api/mini-app/transactions-list")
        raise HTTPException(status_code=401, detail="Invalid Telegram signature")

    try:
        # Verify account exists
        account_stmt = select(Account).where(Account.id == account_id)
        account_result = await db.execute(account_stmt)
        account = account_result.scalar_one_or_none()

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

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

        where_clause = []
        if scope == "personal":
            where_clause = [
                (Transaction.from_account_id == account_id)
                | (Transaction.to_account_id == account_id)
            ]

        trans_stmt = select(
            Transaction.from_account_id,
            from_account_alias.label("from_ac_name"),
            Transaction.to_account_id,
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
                from_account_id=row[0],
                from_ac_name=row[1] or "Unknown",
                to_account_id=row[2],
                to_ac_name=row[3] or "Unknown",
                amount=float(row[4]),
                date=row[5].isoformat() if row[5] else "",
                description=row[6],
            )
            for row in transactions_data
        ]

        return TransactionListResponse(transactions=transactions_list_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/mini-app/transactions-list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server error") from e


@router.post("/bills")
async def get_bills(
    account_id: int,
    authorization: str | None = Header(None),  # noqa: B008
    x_telegram_init_data: str | None = Header(None),  # noqa: B008
    body: dict[str, Any] | None = Body(None),  # noqa: B008
    db: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> BillsListResponse:
    """Get list of all bills (electricity, shared electricity, conservation, main) for a specific account.

    Returns bills for the account itself and for properties owned by the account owner.
    Each bill includes period information, bill type, and amount.

    Args:
        account_id: Account ID to fetch bills for (required, extracted during page initialization).

    Returns:
        BillsListResponse with list of bills sorted by period (most recent first).

    Raises:
        400: Missing or invalid account_id
        401: Invalid Telegram signature
        404: Account not found
        500: Server error
    """
    from src.models.bill import Bill
    from src.models.property import Property
    from src.models.service_period import ServicePeriod

    # Validate account_id
    if not account_id or account_id <= 0:
        raise HTTPException(status_code=400, detail="Valid account_id required")

    # Extract and verify init data (for authentication only)
    init_data_raw = _extract_init_data(authorization, x_telegram_init_data, body)
    parsed_data = UserService.verify_telegram_webapp_signature(
        init_data=init_data_raw or "", bot_token=bot_config.telegram_bot_token
    )

    if not parsed_data:
        logger.warning("Invalid Telegram signature in /api/mini-app/bills")
        raise HTTPException(status_code=401, detail="Invalid Telegram signature")

    try:
        # Verify account exists and get its user_id
        account_stmt = select(Account).where(Account.id == account_id)
        account_result = await db.execute(account_stmt)
        account = account_result.scalar_one_or_none()

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Get properties owned by account's user
        user_property_ids = []
        if account.user_id:
            user_properties_stmt = select(Property.id).where(Property.owner_id == account.user_id)
            result = await db.execute(user_properties_stmt)
            user_property_ids = [row[0] for row in result.all()]

        # Build reading subqueries
        start_reading_alias, end_reading_alias = _build_electricity_reading_subqueries("both")

        # Build where clause for account and owner properties
        where_clause = [Bill.account_id == account_id]
        if user_property_ids:
            from sqlalchemy import or_

            where_clause = [
                or_(Bill.account_id == account_id, Bill.property_id.in_(user_property_ids))
            ]

        # Query bills
        bills_stmt = (
            select(Bill, ServicePeriod, Property, start_reading_alias, end_reading_alias)
            .join(ServicePeriod, Bill.service_period_id == ServicePeriod.id)
            .outerjoin(Property, Bill.property_id == Property.id)
            .where(*where_clause)
            .order_by(ServicePeriod.start_date.desc())
        )

        result = await db.execute(bills_stmt)
        bills_data = result.all()

        # Build response list
        bills_response = []
        for row_data in bills_data:
            bill = row_data[0]
            service_period = row_data[1]
            property_obj = row_data[2]

            start_reading = None
            end_reading = None
            if bill.bill_type.value == "electricity":
                start_reading = float(row_data[3]) if row_data[3] else None
                end_reading = float(row_data[4]) if row_data[4] else None

            bill_response = _format_bill_response(
                bill, service_period, property_obj, start_reading, end_reading
            )
            bills_response.append(bill_response)

        return {"bills": bills_response}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/mini-app/bills: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server error") from e


# Balance Response Models
class BalanceResponse(BaseModel):
    """Response schema for single user balance endpoint."""

    balance: float  # Raw balance value
    invert_for_display: bool = False  # True for OWNER accounts (display negated value)

    model_config = ConfigDict(from_attributes=True)


class AccountItem(BaseModel):
    """Response schema for a single account's info item."""

    account_id: int  # Account ID for navigation
    account_name: str
    account_type: str  # 'owner', 'staff', or 'organization'
    balance: float
    invert_for_display: bool = False  # True for OWNER accounts

    model_config = ConfigDict(from_attributes=True)


class AccountsResponse(BaseModel):
    """Response schema for accounts endpoint."""

    accounts: list[AccountItem]

    model_config = ConfigDict(from_attributes=True)


@router.post("/balance", response_model=BalanceResponse)
async def get_balance(
    account_id: int,
    authorization: str | None = Header(None),  # noqa: B008
    x_telegram_init_data: str | None = Header(None),  # noqa: B008
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    body: dict[str, Any] | None = Body(None),  # noqa: B008
) -> BalanceResponse:
    """Get balance (payments - bills) for a specific account.

    Args:
        account_id: Account ID to calculate balance for (required, extracted during page initialization).

    Returns:
        BalanceResponse with balance value (positive = credit, negative = debt).

    Raises:
        400: Missing or invalid account_id
        401: Invalid Telegram signature
        404: Account not found
        500: Server error
    """
    # Validate account_id
    if not account_id or account_id <= 0:
        raise HTTPException(status_code=400, detail="Valid account_id required")

    try:
        # Extract init data (for authentication only)
        raw_init_data = _extract_init_data(authorization, x_telegram_init_data, body)
        if not raw_init_data:
            raise HTTPException(status_code=400, detail="Missing init data")

        # Verify Telegram signature
        parsed_data = UserService.verify_telegram_webapp_signature(
            init_data=raw_init_data, bot_token=bot_config.telegram_bot_token
        )
        if not parsed_data:
            raise HTTPException(status_code=401, detail="Invalid Telegram signature")

        # Verify account exists
        account_stmt = select(Account).where(Account.id == account_id)
        account_result = await session.execute(account_stmt)
        account = account_result.scalar_one_or_none()

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Calculate balance using service
        from src.services.balance_service import BalanceCalculationService

        balance_service = BalanceCalculationService(session)
        result = await balance_service.calculate_account_balance_with_display(account_id)

        return BalanceResponse(balance=result.balance, invert_for_display=result.invert_for_display)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/mini-app/balance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server error") from e


@router.post("/accounts", response_model=AccountsResponse)
async def get_all_accounts(
    authorization: str | None = Header(None),  # noqa: B008
    x_telegram_init_data: str | None = Header(None),  # noqa: B008
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    body: dict[str, Any] | None = Body(None),  # noqa: B008
) -> AccountsResponse:
    """Get accounts for all owners (info available to any owner)."""
    try:
        # Extract init data
        raw_init_data = _extract_init_data(authorization, x_telegram_init_data, body)
        if not raw_init_data:
            raise HTTPException(status_code=400, detail="Missing init data")

        # Verify Telegram signature
        parsed_data = UserService.verify_telegram_webapp_signature(
            init_data=raw_init_data, bot_token=bot_config.telegram_bot_token
        )
        if not parsed_data:
            raise HTTPException(status_code=401, detail="Invalid Telegram signature")

        # Extract telegram_id from parsed data
        user_data = json.loads(parsed_data.get("user", "{}"))
        telegram_id = str(user_data.get("id"))
        if not telegram_id:
            raise HTTPException(status_code=401, detail="User ID not found in init data")

        # Get the authenticated user
        stmt = select(User).filter(User.telegram_id == int(telegram_id))
        result = await session.execute(stmt)
        authenticated_user = result.scalar_one_or_none()
        if not authenticated_user:
            raise HTTPException(status_code=401, detail="User not found")

        # Get all accounts (user + organization) for balance display
        # All owners can view all account balances - info is not restricted
        from src.models.account import Account
        from src.services.balance_service import BalanceCalculationService

        stmt = select(Account)
        result = await session.execute(stmt)
        accounts = result.scalars().all()

        accounts_list = []
        balance_service = BalanceCalculationService(session)

        for account in accounts:
            # Calculate balance using service with display info
            result = await balance_service.calculate_account_balance_with_display(account.id)

            # Handle account_type as either Enum or string
            account_type_str = (
                account.account_type.value
                if hasattr(account.account_type, "value")
                else str(account.account_type)
            )

            accounts_list.append(
                AccountItem(
                    account_id=account.id,
                    account_name=account.name,
                    account_type=account_type_str,
                    balance=result.balance,
                    invert_for_display=result.invert_for_display,
                )
            )

        return AccountsResponse(accounts=accounts_list)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/mini-app/accounts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server error") from e


# Endpoints will be implemented in Phase 5 and Polish
# - GET /api/mini-app/verify-registration
# - POST /api/mini-app/menu-action


__all__ = ["router"]
