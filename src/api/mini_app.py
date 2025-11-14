"""Mini App API endpoints."""

import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.config import bot_config
from src.services import get_async_session
from src.services.user_service import UserService, UserStatusService

logger = logging.getLogger(__name__)

# Create router for Mini App endpoints
router = APIRouter(prefix="/api/mini-app", tags=["mini-app"])


# Response schemas
class UserStatusResponse(BaseModel):
    """Response schema for user status endpoint."""

    user_id: int
    roles: list[str]  # e.g., ["investor", "owner", "stakeholder"]
    stakeholder_url: str | None  # URL from environment, may be null
    share_percentage: int | None  # 1 (signed), 0 (unsigned owner), None (non-owner)

    model_config = ConfigDict(from_attributes=True)


@router.get("/config")
async def get_config() -> dict[str, Any]:
    """
    Get Mini App configuration from environment variables.

    Returns public configuration values like photo gallery URL.

    Returns:
        {"photoGalleryUrl": str | null}
    """
    try:
        photo_gallery_url = os.getenv("PHOTO_GALLERY_URL")
        return {"photoGalleryUrl": photo_gallery_url}
    except Exception as e:
        logger.error(f"Error in /api/mini-app/config: {e}", exc_info=True)
        return {"photoGalleryUrl": None}


@router.get("/init")
async def mini_app_init(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> dict[str, Any]:
    """
    Initialize Mini App and verify user registration status.

    Returns user access status and menu configuration for registered users,
    or access denied message for non-registered users.

    Args:
        x_telegram_init_data: Telegram WebApp initData (signature verification)
        session: Database session

    Returns:
        For registered users: {"isRegistered": true, "menu": [...], "userName": ...}
        For non-registered: {"isRegistered": false, "message": "Access is limited", ...}

    Raises:
        401: Invalid Telegram signature
        500: Server error
    """
    try:
        # Verify Telegram signature
        parsed_data = UserService.verify_telegram_webapp_signature(
            init_data=x_telegram_init_data, bot_token=bot_config.telegram_bot_token
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


@router.get("/verify-registration")
async def verify_registration(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> dict[str, Any]:
    """
    Verify user registration status (explicit refresh).

    Similar to /init but provides just registration status without menu.
    Useful for explicit refresh after user requests it.

    Args:
        x_telegram_init_data: Telegram WebApp initData
        session: Database session

    Returns:
        {"isRegistered": bool, "userId": str, ...}

    Raises:
        401: Invalid Telegram signature
    """
    try:
        # Verify signature
        parsed_data = UserService.verify_telegram_webapp_signature(
            init_data=x_telegram_init_data, bot_token=bot_config.telegram_bot_token
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
async def menu_action(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    action_data: dict[str, Any] = None,
) -> dict[str, Any]:
    """
    Handle menu action (placeholder for future features).

    Args:
        x_telegram_init_data: Telegram WebApp initData
        action_data: Action data (e.g., {"action": "rule", "data": {}})

    Returns:
        {"success": bool, "message": str}

    Raises:
        401: Invalid signature or not registered
        403: Access denied
    """
    try:
        # Verify signature
        parsed_data = UserService.verify_telegram_webapp_signature(
            init_data=x_telegram_init_data, bot_token=bot_config.telegram_bot_token
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


@router.get("/user-status", response_model=UserStatusResponse)
async def get_user_status(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> UserStatusResponse:
    """
    Get current user's status information for dashboard display.

    Returns user's active roles, stakeholder contract status (for owners),
    and stakeholder shares link (for owners only).

    Args:
        x_telegram_init_data: Telegram WebApp initData (signature verification)
        session: Database session

    Returns:
        UserStatusResponse with user_id, roles, stakeholder_url, share_percentage

    Raises:
        401: Invalid Telegram signature
        403: User not registered or inactive
        500: Server error
    """
    try:
        # Verify Telegram signature
        parsed_data = UserService.verify_telegram_webapp_signature(
            init_data=x_telegram_init_data, bot_token=bot_config.telegram_bot_token
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

        return UserStatusResponse(
            user_id=user.id,
            roles=roles,
            stakeholder_url=stakeholder_url,
            share_percentage=share_percentage,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /api/mini-app/user-status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server error") from e


# Endpoints will be implemented in Phase 5 and Polish
# - GET /api/mini-app/verify-registration
# - POST /api/mini-app/menu-action


__all__ = ["router"]
