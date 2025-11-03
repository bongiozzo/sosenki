"""Admin request handling API routes (US3)."""

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.admin import AdminActionPayload, AdminActionResponse
from backend.app.schemas.requests import RequestResponse
from backend.app.services.admin_service import (
    accept_request,
    reject_request,
    get_pending_requests,
    UserAlreadyExistsError,
)
from backend.app.logging import logger

router = APIRouter(prefix="/admin/requests", tags=["admin"])


@router.get("", response_model=list[RequestResponse])
async def list_requests(db: Session = Depends(get_db)) -> list[RequestResponse]:
    """
    List all pending requests (US3 — Admin list).

    Returns:
        200: List of pending TelegramUserCandidate records
    """
    try:
        requests = get_pending_requests(db=db)
        logger.info(f"Admin listed {len(requests)} pending requests")
        return [RequestResponse.model_validate(req) for req in requests]
    except Exception as e:
        logger.error(f"Error listing requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list requests",
        )


@router.post(
    "/{request_id}/action", response_model=AdminActionResponse, status_code=status.HTTP_200_OK
)
async def perform_action(
    request_id: int,
    payload: AdminActionPayload,
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    """
    Perform an admin action on a pending request (accept or reject).

    Args:
        request_id: ID of the request
        payload: Action details (action, admin_id, optional reason)

    Returns:
        200: AdminActionResponse
        400: UserAlreadyExistsError when user exists
        409: Conflict when user already exists
        404: Request not found
        422: Invalid action
    """
    if payload.action not in ["accept", "reject"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Action must be 'accept' or 'reject'",
        )

    try:
        if payload.action == "accept":
            accept_request(
                db=db,
                request_id=request_id,
                admin_id=payload.admin_id,
            )
            logger.info(f"Request {request_id} accepted by admin {payload.admin_id}")
            # Return a dummy AdminAction response (in practice, fetch it)
            # For now, return 200 with user info
            from backend.app.models.admin_action import AdminAction

            audit = (
                db.query(AdminAction)
                .filter_by(admin_id=payload.admin_id, request_id=request_id)
                .first()
            )
            return AdminActionResponse.model_validate(audit)

        else:  # reject
            reject_request(
                db=db,
                request_id=request_id,
                admin_id=payload.admin_id,
                reason=payload.reason,
            )
            logger.info(f"Request {request_id} rejected by admin {payload.admin_id}")
            from backend.app.models.admin_action import AdminAction

            audit = (
                db.query(AdminAction)
                .filter_by(admin_id=payload.admin_id, request_id=request_id)
                .first()
            )
            return AdminActionResponse.model_validate(audit)

    except UserAlreadyExistsError as e:
        logger.warning(f"User already exists error: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValueError as e:
        logger.error(f"Request not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error performing action on request {request_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform action",
        )
