"""Payment management API endpoints.

Handles financial operations:
- Service period management (OPEN/CLOSED)
- Contribution recording and tracking
- Expense tracking with payer attribution
- Balance calculations and reporting
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from src.services.payment_service import PaymentService
from src.services.balance_service import BalanceService
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


class BudgetItemCreateRequest(BaseModel):
    """Request to create a budget item."""
    payment_type: str = Field(..., min_length=1, max_length=100)
    budgeted_cost: Decimal = Field(..., gt=0, decimal_places=2)
    allocation_strategy: str = Field(..., pattern="^(PROPORTIONAL|FIXED_FEE|USAGE_BASED|NONE)$")


class BudgetItemResponse(BaseModel):
    """Response with budget item details."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    service_period_id: int
    payment_type: str
    budgeted_cost: Decimal
    allocation_strategy: str
    description: Optional[str] = None


class MeterReadingCreateRequest(BaseModel):
    """Request to record a meter reading."""
    meter_name: str = Field(..., min_length=1, max_length=255)
    meter_start_reading: Decimal = Field(...)
    meter_end_reading: Decimal = Field(...)
    calculated_total_cost: Decimal = Field(..., ge=0, decimal_places=2)
    unit: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None


class MeterReadingResponse(BaseModel):
    """Response with meter reading details."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    service_period_id: int
    meter_name: str
    meter_start_reading: Decimal
    meter_end_reading: Decimal
    calculated_total_cost: Decimal
    unit: Optional[str]
    description: Optional[str]
    recorded_at: datetime


class ServiceChargeCreateRequest(BaseModel):
    """Request to record a service charge."""
    user_id: int
    description: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., gt=0, decimal_places=2)


class ServiceChargeUpdateRequest(BaseModel):
    """Request to update a service charge."""
    description: Optional[str] = Field(None, min_length=1, max_length=255)
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)


class ServiceChargeResponse(BaseModel):
    """Response with service charge details."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    service_period_id: int
    user_id: int
    description: str
    amount: Decimal


class BalanceSheetEntryResponse(BaseModel):
    """Balance sheet entry for owner in period."""
    owner_id: int
    username: str
    total_contributions: Decimal
    total_expenses: Decimal
    total_charges: Decimal
    balance: Decimal  # contributions - (expenses + charges)


class BalanceSheetResponse(BaseModel):
    """Complete balance sheet for period."""
    period_id: int
    entries: List[BalanceSheetEntryResponse]
    total_period_balance: Decimal


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


# ============================================================================
# Budget Item Endpoints
# ============================================================================

@router.post("/periods/{period_id}/budget-items", response_model=BudgetItemResponse, status_code=status.HTTP_201_CREATED)
async def create_budget_item(
    period_id: int,
    request: BudgetItemCreateRequest,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> BudgetItemResponse:
    """Create a budget item for expense allocation.

    Args:
        period_id: Period ID
        request: Budget item details
        db: Database session

    Returns:
        Created budget item details

    Raises:
        HTTPException: If validation fails
    """
    try:
        service = PaymentService(db=db)
        budget_item = service.create_budget_item(
            period_id=period_id,
            payment_type=request.payment_type,
            budgeted_cost=request.budgeted_cost,
            allocation_strategy=request.allocation_strategy,
            description=request.description
        )
        return BudgetItemResponse.model_validate(budget_item)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/periods/{period_id}/budget-items", response_model=List[BudgetItemResponse])
async def list_budget_items(
    period_id: int,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> List[BudgetItemResponse]:
    """List budget items for a period.

    Args:
        period_id: Period ID
        db: Database session

    Returns:
        List of budget items
    """
    service = PaymentService(db=db)
    budget_items = service.get_budget_items(period_id)
    return [BudgetItemResponse.model_validate(b) for b in budget_items]


# ============================================================================
# Meter Reading Endpoints
# ============================================================================

@router.post("/periods/{period_id}/meter-readings", response_model=MeterReadingResponse, status_code=status.HTTP_201_CREATED)
async def record_meter_reading(
    period_id: int,
    request: MeterReadingCreateRequest,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> MeterReadingResponse:
    """Record a meter reading for usage-based billing.

    Args:
        period_id: Period ID
        request: Meter reading details
        db: Database session

    Returns:
        Recorded meter reading

    Raises:
        HTTPException: If period not found or validation fails
    """
    service = PaymentService(db=db)
    try:
        reading = service.record_meter_reading(
            period_id=period_id,
            meter_name=request.meter_name,
            meter_start_reading=request.meter_start_reading,
            meter_end_reading=request.meter_end_reading,
            calculated_total_cost=request.calculated_total_cost,
            unit=request.unit,
            description=request.description,
        )
        return MeterReadingResponse.model_validate(reading)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/periods/{period_id}/meter-readings", response_model=List[MeterReadingResponse])
async def list_meter_readings(
    period_id: int,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> List[MeterReadingResponse]:
    """List all meter readings for a period.

    Args:
        period_id: Period ID
        db: Database session

    Returns:
        List of meter readings
    """
    service = PaymentService(db=db)
    readings = service.get_meter_readings(period_id)
    return [MeterReadingResponse.model_validate(r) for r in readings]


# ============================================================================
# Service Charge Endpoints
# ============================================================================

@router.post("/periods/{period_id}/service-charges", response_model=ServiceChargeResponse, status_code=status.HTTP_201_CREATED)
async def record_service_charge(
    period_id: int,
    request: ServiceChargeCreateRequest,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> ServiceChargeResponse:
    """Record a service charge for a specific owner.

    Args:
        period_id: Period ID
        request: Service charge details
        db: Database session

    Returns:
        Recorded service charge

    Raises:
        HTTPException: If period not found, closed, or validation fails
    """
    service = PaymentService(db=db)
    try:
        charge = service.record_service_charge(
            period_id=period_id,
            user_id=request.user_id,
            description=request.description,
            amount=request.amount,
        )
        return ServiceChargeResponse.model_validate(charge)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/periods/{period_id}/service-charges", response_model=List[ServiceChargeResponse])
async def list_service_charges(
    period_id: int,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> List[ServiceChargeResponse]:
    """List all service charges for a period.

    Args:
        period_id: Period ID
        db: Database session

    Returns:
        List of service charges
    """
    service = PaymentService(db=db)
    charges = service.get_service_charges(period_id)
    return [ServiceChargeResponse.model_validate(c) for c in charges]


@router.get("/service-charges/{charge_id}", response_model=ServiceChargeResponse)
async def get_service_charge(
    charge_id: int,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> ServiceChargeResponse:
    """Get a specific service charge by ID.

    Args:
        charge_id: Service charge ID
        db: Database session

    Returns:
        Service charge details

    Raises:
        HTTPException: If charge not found
    """
    service = PaymentService(db=db)
    charge = service.get_service_charge(charge_id)
    if not charge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service charge not found")
    return ServiceChargeResponse.model_validate(charge)


@router.patch("/service-charges/{charge_id}", response_model=ServiceChargeResponse)
async def update_service_charge(
    charge_id: int,
    request: ServiceChargeUpdateRequest,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> ServiceChargeResponse:
    """Update a service charge.

    Args:
        charge_id: Service charge ID
        request: Update details
        db: Database session

    Returns:
        Updated service charge

    Raises:
        HTTPException: If charge not found or period is closed
    """
    service = PaymentService(db=db)
    try:
        charge = service.update_service_charge(
            charge_id=charge_id,
            description=request.description,
            amount=request.amount,
        )
        if not charge:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service charge not found")
        return ServiceChargeResponse.model_validate(charge)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/service-charges/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_charge(
    charge_id: int,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> None:
    """Delete a service charge.

    Args:
        charge_id: Service charge ID
        db: Database session

    Raises:
        HTTPException: If charge not found or period is closed
    """
    service = PaymentService(db=db)
    try:
        deleted = service.delete_service_charge(charge_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service charge not found")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# Balance Sheet Endpoints
# ============================================================================

@router.get("/periods/{period_id}/balance-sheet", response_model=BalanceSheetResponse)
async def get_period_balance_sheet(
    period_id: int,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> BalanceSheetResponse:
    """Generate balance sheet for entire period.

    Shows all owners with their contributions, expenses, charges, and balance.

    Args:
        period_id: Period ID
        db: Database session

    Returns:
        Complete balance sheet for period

    Raises:
        HTTPException: If period not found
    """
    service = BalanceService(db=db)
    
    # Verify period exists
    payment_service = PaymentService(db=db)
    period = payment_service.get_period(period_id)
    if not period:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Period not found")
    
    sheet = service.generate_period_balance_sheet(period_id)
    total_balance = service.get_period_total_balance(period_id)
    
    entries = [BalanceSheetEntryResponse(**entry) for entry in sheet]
    return BalanceSheetResponse(
        period_id=period_id,
        entries=entries,
        total_period_balance=total_balance
    )


@router.get("/periods/{period_id}/owner-balance/{owner_id}", response_model=Dict)
async def get_owner_balance(
    period_id: int,
    owner_id: int,
    db: Session = Depends(lambda: None)  # TODO: Add proper DB dependency
) -> Dict:
    """Get balance details for specific owner in period.

    Args:
        period_id: Period ID
        owner_id: Owner ID
        db: Database session

    Returns:
        Owner's balance details

    Raises:
        HTTPException: If period or owner not found
    """
    service = BalanceService(db=db)
    
    # Verify period exists
    payment_service = PaymentService(db=db)
    period = payment_service.get_period(period_id)
    if not period:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Period not found")
    
    contrib = service.get_owner_contributions(period_id, owner_id)
    expense = service.get_owner_expenses(period_id, owner_id)
    charge = service.get_owner_service_charges(period_id, owner_id)
    balance = service.get_owner_balance(period_id, owner_id)
    
    return {
        "owner_id": owner_id,
        "period_id": period_id,
        "total_contributions": contrib,
        "total_expenses": expense,
        "total_charges": charge,
        "balance": balance
    }
