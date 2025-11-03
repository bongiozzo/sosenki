"""Request submission API routes (US2)."""

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.requests import CreateRequestPayload, RequestResponse
from backend.app.services.request_service import create_request, DuplicateRequestError
from backend.app.logging import logger

router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("", response_model=RequestResponse, status_code=status.HTTP_201_CREATED)
async def submit_request(
    payload: CreateRequestPayload, db: Session = Depends(get_db)
) -> RequestResponse:
    """
    Submit a new request to join (US2 — Request submission).

    Returns:
        201: RequestResponse with created record
        400: Conflict if duplicate telegram_id
        422: Validation error if required fields missing
    """
    try:
        candidate = create_request(
            db=db,
            telegram_id=payload.telegram_id,
            username=payload.telegram_username,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone=payload.phone,
            email=payload.email,
            note=payload.note,
        )
        logger.info(f"Request submitted successfully for telegram_id: {payload.telegram_id}")
        return RequestResponse.model_validate(candidate)
    except DuplicateRequestError as e:
        logger.warning(f"Duplicate request rejected: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error submitting request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create request",
        )
