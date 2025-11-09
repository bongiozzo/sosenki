"""Payment management API endpoints.

Handles financial operations:
- Service period management (OPEN/CLOSED)
- Contribution recording and tracking
- Expense tracking with payer attribution
- Balance calculations and reporting
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from src.services.payment_service import PaymentService
from src.models import PeriodStatus

router = APIRouter(prefix="/api/payments", tags=["payments"])


# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================

class PeriodCreateRequest(BaseModel):
    """Request to create a service period."""
    name: str = Field(..., min_length=1, max_length=100)
    start_date: date
    end_date: date
    description: Optional[str] = None


class PeriodResponse(BaseModel):
    """Response with service period details."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    start_date: date
    end_date: date
    status: str
    description: Optional[str] = None
    closed_at: Optional[datetime] = None


class ContributionCreateRequest(BaseModel):
    """Request to record a contribution."""
    user_id: int
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    comment: Optional[str] = None


class ContributionResponse(BaseModel):
    """Response with contribution details."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    service_period_id: int
    user_id: int
    amount: Decimal
    date: datetime
    comment: Optional[str] = None


class ExpenseCreateRequest(BaseModel):
    """Request to record an expense."""
    paid_by_user_id: int
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    payment_type: str = Field(..., min_length=1, max_length=100)
    vendor: Optional[str] = None
    description: Optional[str] = None
    budget_item_id: Optional[int] = None


class ExpenseResponse(BaseModel):
    """Response with expense details."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    service_period_id: int
    paid_by_user_id: int
    amount: Decimal
    payment_type: str
    date: datetime
    vendor: Optional[str] = None
    description: Optional[str] = None
    budget_item_id: Optional[int] = None


class ServiceChargeCreateRequest(BaseModel):
    """Request to record a service charge."""
    user_id: int
    description: str = Field(..., min_length=1, max_length=200)
    amount: Decimal = Field(..., gt=0, decimal_places=2)


class ServiceChargeResponse(BaseModel):
    """Response with service charge details."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    service_period_id: int
    user_id: int
    description: str
    amount: Decimal


class OwnerContributionSummary(BaseModel):
    """Summary of owner contributions in a period."""
    owner_id: int
    total_contributed: Decimal


# ============================================================================
# Service Period Endpoints
# ============================================================================

@router.post("/periods", response_model=PeriodResponse, status_code=status.HTTP_201_CREATED)
async def create_period(
    request: PeriodCreateRequest,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> PeriodResponse:
    """Create a new service period.

    Args:
        request: Period creation details
        db: Database session

    Returns:
        Created period details

    Raises:
        HTTPException: If validation fails
    """
    try:
        service = PaymentService(db=db)
        period = service.create_period(
            name=request.name,
            start_date=request.start_date,
            end_date=request.end_date,
            description=request.description
        )
        return PeriodResponse.model_validate(period)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/periods/{period_id}", response_model=PeriodResponse)
async def get_period(
    period_id: int,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> PeriodResponse:
    """Get service period by ID.

    Args:
        period_id: Period ID
        db: Database session

    Returns:
        Period details

    Raises:
        HTTPException: If period not found
    """
    service = PaymentService(db=db)
    period = service.get_period(period_id)
    if not period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Period {period_id} not found"
        )
    return PeriodResponse.model_validate(period)


@router.get("/periods", response_model=List[PeriodResponse])
async def list_periods(
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> List[PeriodResponse]:
    """List all service periods.

    Returns:
        List of periods sorted by start_date descending
    """
    service = PaymentService(db=db)
    periods = service.list_periods()
    return [PeriodResponse.model_validate(p) for p in periods]


@router.post("/periods/{period_id}/close", response_model=PeriodResponse)
async def close_period(
    period_id: int,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> PeriodResponse:
    """Close a service period (finalize balances).

    Args:
        period_id: Period to close
        db: Database session

    Returns:
        Updated period details

    Raises:
        HTTPException: If period not found or already closed
    """
    try:
        service = PaymentService(db=db)
        period = service.close_period(period_id)
        return PeriodResponse.model_validate(period)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/periods/{period_id}/reopen", response_model=PeriodResponse)
async def reopen_period(
    period_id: int,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> PeriodResponse:
    """Reopen a closed period for corrections.

    Args:
        period_id: Period to reopen
        db: Database session

    Returns:
        Updated period details

    Raises:
        HTTPException: If period not found or already open
    """
    try:
        service = PaymentService(db=db)
        period = service.reopen_period(period_id)
        return PeriodResponse.model_validate(period)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# Contribution Endpoints
# ============================================================================

@router.post("/periods/{period_id}/contributions", response_model=ContributionResponse, status_code=status.HTTP_201_CREATED)
async def record_contribution(
    period_id: int,
    request: ContributionCreateRequest,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> ContributionResponse:
    """Record an owner contribution.

    Args:
        period_id: Period ID
        request: Contribution details
        db: Database session

    Returns:
        Created contribution details

    Raises:
        HTTPException: If validation fails
    """
    try:
        service = PaymentService(db=db)
        contribution = service.record_contribution(
            period_id=period_id,
            user_id=request.user_id,
            amount=request.amount,
            date_val=datetime.now(),
            comment=request.comment
        )
        return ContributionResponse.model_validate(contribution)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/periods/{period_id}/contributions", response_model=List[ContributionResponse])
async def list_contributions(
    period_id: int,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> List[ContributionResponse]:
    """List contributions in a period.

    Args:
        period_id: Period ID
        db: Database session

    Returns:
        List of contributions
    """
    service = PaymentService(db=db)
    contributions = service.get_contributions(period_id)
    return [ContributionResponse.model_validate(c) for c in contributions]


@router.get("/periods/{period_id}/owners/{owner_id}/contributions", response_model=OwnerContributionSummary)
async def get_owner_contributions(
    period_id: int,
    owner_id: int,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> OwnerContributionSummary:
    """Get owner's total contributions in a period.

    Args:
        period_id: Period ID
        owner_id: Owner ID
        db: Database session

    Returns:
        Total contributions for owner
    """
    service = PaymentService(db=db)
    total = service.get_owner_contributions(period_id, owner_id)
    return OwnerContributionSummary(owner_id=owner_id, total_contributed=total)


# ============================================================================
# Expense Endpoints
# ============================================================================

@router.post("/periods/{period_id}/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def record_expense(
    period_id: int,
    request: ExpenseCreateRequest,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> ExpenseResponse:
    """Record a community expense.

    Args:
        period_id: Period ID
        request: Expense details
        db: Database session

    Returns:
        Created expense details

    Raises:
        HTTPException: If validation fails
    """
    try:
        service = PaymentService(db=db)
        expense = service.record_expense(
            period_id=period_id,
            paid_by_user_id=request.paid_by_user_id,
            amount=request.amount,
            payment_type=request.payment_type,
            date_val=datetime.now(),
            vendor=request.vendor,
            description=request.description,
            budget_item_id=request.budget_item_id
        )
        return ExpenseResponse.model_validate(expense)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/periods/{period_id}/expenses", response_model=List[ExpenseResponse])
async def list_expenses(
    period_id: int,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> List[ExpenseResponse]:
    """List expenses in a period.

    Args:
        period_id: Period ID
        db: Database session

    Returns:
        List of expenses
    """
    service = PaymentService(db=db)
    expenses = service.get_expenses(period_id)
    return [ExpenseResponse.model_validate(e) for e in expenses]


# ============================================================================
# Service Charge Endpoints
# ============================================================================

@router.post("/periods/{period_id}/charges", response_model=ServiceChargeResponse, status_code=status.HTTP_201_CREATED)
async def record_service_charge(
    period_id: int,
    request: ServiceChargeCreateRequest,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> ServiceChargeResponse:
    """Record a service charge for an owner.

    Args:
        period_id: Period ID
        request: Charge details
        db: Database session

    Returns:
        Created charge details

    Raises:
        HTTPException: If validation fails
    """
    try:
        service = PaymentService(db=db)
        charge = service.record_service_charge(
            period_id=period_id,
            user_id=request.user_id,
            description=request.description,
            amount=request.amount
        )
        return ServiceChargeResponse.model_validate(charge)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/periods/{period_id}/charges", response_model=List[ServiceChargeResponse])
async def list_service_charges(
    period_id: int,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> List[ServiceChargeResponse]:
    """List service charges in a period.

    Args:
        period_id: Period ID
        db: Database session

    Returns:
        List of charges
    """
    service = PaymentService(db=db)
    charges = service.get_service_charges(period_id)
    return [ServiceChargeResponse.model_validate(c) for c in charges]


# TODO: Implement endpoints
