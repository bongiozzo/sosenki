"""MiniApp authentication routes (Telegram Mini App initData verification)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.errors import InvalidInitDataError, raise_app_error
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.logging import logger
from backend.app.models.user import SOSenkiUser
from backend.app.schemas.miniapp import (
    InitDataRequest,
    MiniAppAuthResponse,
    RequestFormResponse,
    UserResponse,
)
from backend.app.services.telegram_auth_service import verify_initdata

router = APIRouter(prefix="/miniapp", tags=["miniapp"])


@router.post("/auth", response_model=MiniAppAuthResponse)
async def miniapp_auth(
    request: InitDataRequest,
    db: Session = Depends(get_db),
) -> MiniAppAuthResponse:
    """
    Authenticate a Telegram Mini App user via initData.

    Endpoint: POST /miniapp/auth

    Flow:
    1. Verify initData signature using bot token
    2. Extract telegram_id from verified user data
    3. Look up SOSenkiUser by telegram_id
    4. If found (linked): return linked=true + user object
    5. If not found (unlinked): return linked=false + request_form pre-fill

    Request:
        - init_data: URL-encoded initData string from Telegram Web App

    Response:
        - linked=true case: { "linked": true, "user": {...} }
        - linked=false case: { "linked": false, "request_form": {...} }

    Errors:
        - 401: Invalid or expired initData

    OpenAPI Reference:
        specs/001-seamless-telegram-auth/contracts/openapi.yaml POST /miniapp/auth
    """
    try:
        # Verify initData signature
        verified_data = verify_initdata(
            request.init_data,
            settings.telegram_bot_token,
            settings.initdata_max_age_seconds,
        )
        telegram_id = verified_data["telegram_id"]
        user_data = verified_data["user"]
        logger.info(f"Verified initData for telegram_id={telegram_id}")

    except InvalidInitDataError as e:
        logger.warning(f"initData verification failed: {e}")
        raise_app_error(e)

    # Query for existing SOSenkiUser
    existing_user = db.query(SOSenkiUser).filter_by(telegram_id=telegram_id).first()

    if existing_user:
        # User is linked
        logger.info(f"User linked: telegram_id={telegram_id}, user_id={existing_user.id}")
        user_response = UserResponse(
            id=str(existing_user.id),
            telegram_id=existing_user.telegram_id,
            first_name=existing_user.first_name,
            last_name=existing_user.last_name,
            email=existing_user.email,
            roles=existing_user.roles or ["User"],
        )
        return MiniAppAuthResponse(
            linked=True,
            user=user_response,
            request_form=None,
        )

    else:
        # User is unlinked - provide request form pre-fill
        logger.info(f"User unlinked: telegram_id={telegram_id}, showing request form")
        request_form = RequestFormResponse(
            telegram_id=telegram_id,
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            photo_url=user_data.get("photo_url"),
        )
        return MiniAppAuthResponse(
            linked=False,
            user=None,
            request_form=request_form,
        )
