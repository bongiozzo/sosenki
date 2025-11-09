"""Payment service for recording and managing financial transactions.

Provides methods for:
- Recording contributions (owner payments)
- Recording expenses (community charges)
- Managing service periods (OPEN/CLOSED)
- Recording service charges
- Transaction history and editing (in OPEN periods)
"""

import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from sqlalchemy.orm import Session

from src.models import (
    ServicePeriod,
    PeriodStatus,
    ContributionLedger,
    ExpenseLedger,
    ServiceCharge,
    BudgetItem,
    UtilityReading,
)

logger = logging.getLogger(__name__)


class PaymentService:
    """Core financial operations service."""

    def __init__(self, db: Optional[Session] = None):
        """Initialize payment service.

        Args:
            db: SQLAlchemy database session (optional for now)
        """
        self.db = db

    def create_period(
        self,
        name: str,
        start_date: date,
        end_date: date,
        description: Optional[str] = None,
    ) -> ServicePeriod:
        """Create a new service period.

        Args:
            name: Period identifier (e.g., "Nov 2025")
            start_date: Period start date
            end_date: Period end date
            description: Optional notes

        Returns:
            Created ServicePeriod object

        Raises:
            ValueError: If start_date >= end_date or period name already exists
        """
        if start_date >= end_date:
            logger.error(f"Invalid period dates: start_date={start_date} >= end_date={end_date}")
            raise ValueError("start_date must be before end_date")

        # Check for duplicate name
        if self.db:
            existing = self.db.query(ServicePeriod).filter_by(name=name).first()
            if existing:
                logger.error(f"Period with name '{name}' already exists")
                raise ValueError(f"Period with name '{name}' already exists")

            period = ServicePeriod(
                name=name,
                start_date=start_date,
                end_date=end_date,
                status=PeriodStatus.OPEN,
                description=description,
            )
            self.db.add(period)
            self.db.commit()
            logger.info(f"Created period: {name} (ID={period.id}, dates: {start_date} to {end_date})")
            self.db.refresh(period)
            return period
        else:
            # Mock implementation for testing
            period = ServicePeriod(
                name=name,
                start_date=start_date,
                end_date=end_date,
                status=PeriodStatus.OPEN,
                description=description,
            )
            return period

    def get_period(self, period_id: int) -> Optional[ServicePeriod]:
        """Get service period by ID.

        Args:
            period_id: Period ID

        Returns:
            ServicePeriod object or None if not found
        """
        if self.db:
            return self.db.query(ServicePeriod).filter_by(id=period_id).first()
        return None

    def list_periods(self) -> List[ServicePeriod]:
        """List all service periods.

        Returns:
            List of ServicePeriod objects sorted by start_date descending
        """
        if self.db:
            return (
                self.db.query(ServicePeriod)
                .order_by(ServicePeriod.start_date.desc())
                .all()
            )
        return []

    def close_period(self, period_id: int) -> ServicePeriod:
        """Close a service period (finalize balances).

        Transitions period from OPEN to CLOSED.
        Prevents further transactions.

        Args:
            period_id: Period to close

        Returns:
            Updated ServicePeriod object

        Raises:
            ValueError: If period not found or already closed
        """
        if self.db:
            period = self.db.query(ServicePeriod).filter_by(id=period_id).first()
            if not period:
                raise ValueError(f"Period {period_id} not found")
            if period.status == PeriodStatus.CLOSED:
                raise ValueError(f"Period {period_id} is already closed")

            period.status = PeriodStatus.CLOSED
            period.closed_at = datetime.now(
                datetime.now().astimezone().tzinfo
            )
            self.db.commit()
            self.db.refresh(period)
            return period
        return None

    def reopen_period(self, period_id: int) -> ServicePeriod:
        """Reopen a closed period for corrections.

        Transitions period from CLOSED to OPEN.
        Allows transaction editing/adding.

        Args:
            period_id: Period to reopen

        Returns:
            Updated ServicePeriod object

        Raises:
            ValueError: If period not found or already open
        """
        if self.db:
            period = self.db.query(ServicePeriod).filter_by(id=period_id).first()
            if not period:
                raise ValueError(f"Period {period_id} not found")
            if period.status == PeriodStatus.OPEN:
                raise ValueError(f"Period {period_id} is already open")

            period.status = PeriodStatus.OPEN
            period.closed_at = None
            self.db.commit()
            self.db.refresh(period)
            return period
        return None

    def record_contribution(
        self,
        period_id: int,
        user_id: int,
        amount: Decimal,
        date_val: datetime,
        comment: Optional[str] = None,
    ) -> ContributionLedger:
        """Record owner contribution (payment).

        Args:
            period_id: Service period ID
            user_id: Owner ID
            amount: Contribution amount
            date_val: Date of contribution
            comment: Optional notes

        Returns:
            Created ContributionLedger object

        Raises:
            ValueError: If period not found, period is closed, or amount is invalid
        """
        if self.db:
            # Validate period
            period = self.db.query(ServicePeriod).filter_by(id=period_id).first()
            if not period:
                logger.error(f"Period {period_id} not found")
                raise ValueError(f"Period {period_id} not found")
            if period.status != PeriodStatus.OPEN:
                logger.error(f"Cannot record contribution in closed period {period_id}")
                raise ValueError(f"Period {period_id} is not open for contributions")

            # Validate amount
            if amount <= Decimal(0):
                logger.error(f"Invalid contribution amount: {amount}")
                raise ValueError("Contribution amount must be positive")

            contribution = ContributionLedger(
                service_period_id=period_id,
                user_id=user_id,
                amount=amount,
                date=date_val,
                comment=comment,
            )
            self.db.add(contribution)
            self.db.commit()
            self.db.refresh(contribution)
            logger.info(f"Recorded contribution: user_id={user_id}, amount={amount}, period_id={period_id}, tx_id={contribution.id}")
            return contribution
        return None

    def get_contributions(self, period_id: int) -> List[ContributionLedger]:
        """List all contributions in period.

        Args:
            period_id: Period ID

        Returns:
            List of ContributionLedger objects sorted by date
        """
        if self.db:
            return (
                self.db.query(ContributionLedger)
                .filter_by(service_period_id=period_id)
                .order_by(ContributionLedger.date)
                .all()
            )
        return []

    def get_owner_contributions(self, period_id: int, owner_id: int) -> Decimal:
        """Get cumulative contributions for owner in period.

        Args:
            period_id: Period ID
            owner_id: Owner ID

        Returns:
            Total contribution amount (Decimal)
        """
        if self.db:
            from sqlalchemy import func

            result = (
                self.db.query(func.sum(ContributionLedger.amount))
                .filter_by(service_period_id=period_id, user_id=owner_id)
                .scalar()
            )
            return Decimal(result or 0)
        return Decimal(0)

    def edit_contribution(
        self,
        contribution_id: int,
        amount: Optional[Decimal] = None,
        comment: Optional[str] = None,
    ) -> ContributionLedger:
        """Edit contribution in OPEN period.

        Args:
            contribution_id: Contribution ID
            amount: New amount (optional)
            comment: New comment (optional)

        Returns:
            Updated ContributionLedger object

        Raises:
            ValueError: If contribution not found or period is closed
        """
        if self.db:
            contribution = self.db.query(ContributionLedger).filter_by(
                id=contribution_id
            ).first()
            if not contribution:
                raise ValueError(f"Contribution {contribution_id} not found")

            # Verify period is open
            period = self.db.query(ServicePeriod).filter_by(
                id=contribution.service_period_id
            ).first()
            if period.status != PeriodStatus.OPEN:
                raise ValueError("Cannot edit contribution in closed period")

            if amount is not None:
                if amount <= Decimal(0):
                    raise ValueError("Contribution amount must be positive")
                contribution.amount = amount

            if comment is not None:
                contribution.comment = comment

            self.db.commit()
            self.db.refresh(contribution)
            return contribution
        return None

    def record_expense(
        self,
        period_id: int,
        paid_by_user_id: int,
        amount: Decimal,
        payment_type: str,
        date_val: datetime,
        vendor: Optional[str] = None,
        description: Optional[str] = None,
        budget_item_id: Optional[int] = None,
    ) -> ExpenseLedger:
        """Record community expense.

        Args:
            period_id: Service period ID
            paid_by_user_id: User who paid the expense
            amount: Expense amount
            payment_type: Category of expense
            date_val: Date of expense
            vendor: Vendor/service provider (optional)
            description: Details (optional)
            budget_item_id: Reference to budget item (optional)

        Returns:
            Created ExpenseLedger object

        Raises:
            ValueError: If period not found, period is closed, or amount is invalid
        """
        if self.db:
            # Validate period
            period = self.db.query(ServicePeriod).filter_by(id=period_id).first()
            if not period:
                raise ValueError(f"Period {period_id} not found")
            if period.status != PeriodStatus.OPEN:
                raise ValueError(f"Period {period_id} is not open for expenses")

            # Validate amount
            if amount <= Decimal(0):
                raise ValueError("Expense amount must be positive")

            expense = ExpenseLedger(
                service_period_id=period_id,
                paid_by_user_id=paid_by_user_id,
                amount=amount,
                payment_type=payment_type,
                date=date_val,
                vendor=vendor,
                description=description,
                budget_item_id=budget_item_id,
            )
            self.db.add(expense)
            self.db.commit()
            self.db.refresh(expense)
            return expense
        return None

    def get_expenses(self, period_id: int) -> List[ExpenseLedger]:
        """List all expenses in period.

        Args:
            period_id: Period ID

        Returns:
            List of ExpenseLedger objects sorted by date
        """
        if self.db:
            return (
                self.db.query(ExpenseLedger)
                .filter_by(service_period_id=period_id)
                .order_by(ExpenseLedger.date)
                .all()
            )
        return []

    def get_paid_by_user(self, period_id: int, user_id: int) -> List[ExpenseLedger]:
        """Get expenses paid by specific user.

        Args:
            period_id: Period ID
            user_id: Payer user ID

        Returns:
            List of ExpenseLedger objects
        """
        if self.db:
            return (
                self.db.query(ExpenseLedger)
                .filter_by(service_period_id=period_id, paid_by_user_id=user_id)
                .order_by(ExpenseLedger.date)
                .all()
            )
        return []

    def edit_expense(
        self,
        expense_id: int,
        amount: Optional[Decimal] = None,
        payment_type: Optional[str] = None,
        vendor: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ExpenseLedger:
        """Edit expense in OPEN period.

        Args:
            expense_id: Expense ID
            amount: New amount (optional)
            payment_type: New type (optional)
            vendor: New vendor (optional)
            description: New description (optional)

        Returns:
            Updated ExpenseLedger object

        Raises:
            ValueError: If expense not found or period is closed
        """
        if self.db:
            expense = self.db.query(ExpenseLedger).filter_by(id=expense_id).first()
            if not expense:
                raise ValueError(f"Expense {expense_id} not found")

            # Verify period is open
            period = self.db.query(ServicePeriod).filter_by(
                id=expense.service_period_id
            ).first()
            if period.status != PeriodStatus.OPEN:
                raise ValueError("Cannot edit expense in closed period")

            if amount is not None:
                if amount <= Decimal(0):
                    raise ValueError("Expense amount must be positive")
                expense.amount = amount

            if payment_type is not None:
                expense.payment_type = payment_type

            if vendor is not None:
                expense.vendor = vendor

            if description is not None:
                expense.description = description

            self.db.commit()
            self.db.refresh(expense)
            return expense
        return None

    def record_service_charge(
        self,
        period_id: int,
        user_id: int,
        description: str,
        amount: Decimal,
    ) -> ServiceCharge:
        """Record service charge for specific owner.

        Args:
            period_id: Period ID
            user_id: Owner to charge
            description: Charge description
            amount: Charge amount

        Returns:
            Created ServiceCharge object

        Raises:
            ValueError: If period not found, period is closed, or amount is invalid
        """
        if self.db:
            # Validate period
            period = self.db.query(ServicePeriod).filter_by(id=period_id).first()
            if not period:
                raise ValueError(f"Period {period_id} not found")
            if period.status != PeriodStatus.OPEN:
                raise ValueError(f"Period {period_id} is not open for charges")

            # Validate amount
            if amount <= Decimal(0):
                raise ValueError("Charge amount must be positive")

            charge = ServiceCharge(
                service_period_id=period_id,
                user_id=user_id,
                description=description,
                amount=amount,
            )
            self.db.add(charge)
            self.db.commit()
            self.db.refresh(charge)
            return charge
        return None

    def get_service_charges(self, period_id: int) -> List[ServiceCharge]:
        """List all service charges in period.

        Args:
            period_id: Period ID

        Returns:
            List of ServiceCharge objects
        """
        if self.db:
            return (
                self.db.query(ServiceCharge)
                .filter_by(service_period_id=period_id)
                .all()
            )
        return []

    def get_service_charge(self, charge_id: int) -> Optional[ServiceCharge]:
        """Get a specific service charge by ID.

        Args:
            charge_id: Service charge ID

        Returns:
            ServiceCharge object or None if not found
        """
        if self.db:
            return self.db.query(ServiceCharge).filter_by(id=charge_id).first()
        return None

    def get_owner_service_charges(self, period_id: int, user_id: int) -> List[ServiceCharge]:
        """Get all service charges for a specific owner in a period.

        Args:
            period_id: Service period ID
            user_id: Owner ID

        Returns:
            List of ServiceCharge objects for owner
        """
        if self.db:
            return (
                self.db.query(ServiceCharge)
                .filter_by(service_period_id=period_id, user_id=user_id)
                .all()
            )
        return []

    def update_service_charge(
        self,
        charge_id: int,
        description: Optional[str] = None,
        amount: Optional[Decimal] = None,
    ) -> Optional[ServiceCharge]:
        """Update a service charge.

        Args:
            charge_id: Service charge ID
            description: New description (optional)
            amount: New amount (optional)

        Returns:
            Updated ServiceCharge object

        Raises:
            ValueError: If charge not found, amount invalid, or period is closed
        """
        if self.db:
            charge = self.db.query(ServiceCharge).filter_by(id=charge_id).first()
            if not charge:
                raise ValueError(f"Service charge {charge_id} not found")

            # Check period is still open
            period = self.db.query(ServicePeriod).filter_by(id=charge.service_period_id).first()
            if period and period.status != PeriodStatus.OPEN:
                raise ValueError(f"Period {charge.service_period_id} is not open for updates")

            if description is not None:
                charge.description = description

            if amount is not None:
                if amount <= Decimal(0):
                    raise ValueError("Charge amount must be positive")
                charge.amount = amount

            self.db.commit()
            self.db.refresh(charge)
            return charge
        return None

    def delete_service_charge(self, charge_id: int) -> bool:
        """Delete a service charge.

        Args:
            charge_id: Service charge ID

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If period is closed
        """
        if self.db:
            charge = self.db.query(ServiceCharge).filter_by(id=charge_id).first()
            if not charge:
                return False

            # Check period is still open
            period = self.db.query(ServicePeriod).filter_by(id=charge.service_period_id).first()
            if period and period.status != PeriodStatus.OPEN:
                raise ValueError(f"Period {charge.service_period_id} is not open for deletions")

            self.db.delete(charge)
            self.db.commit()
            return True
        return False

    def get_transaction_history(
        self,
        period_id: int,
        user_id: Optional[int] = None,
    ) -> List:
        """Get complete transaction history for period.

        Returns contributions, expenses, and charges combined and sorted by date.

        Args:
            period_id: Period ID
            user_id: Optional - filter to specific owner

        Returns:
            List of transactions sorted by date
        """
        if self.db:
            # This is a simplified implementation
            # In production, would use proper transaction representation
            transactions = []

            # Get contributions
            contributions = (
                self.db.query(ContributionLedger)
                .filter_by(service_period_id=period_id)
            )
            if user_id:
                contributions = contributions.filter_by(user_id=user_id)
            transactions.extend(contributions.all())

            # Get expenses
            expenses = (
                self.db.query(ExpenseLedger)
                .filter_by(service_period_id=period_id)
            )
            if user_id:
                # For expenses, user_id refers to paid_by_user_id
                expenses = expenses.filter_by(paid_by_user_id=user_id)
            transactions.extend(expenses.all())

            # Get charges
            charges = (
                self.db.query(ServiceCharge)
                .filter_by(service_period_id=period_id)
            )
            if user_id:
                charges = charges.filter_by(user_id=user_id)
            transactions.extend(charges.all())

            # Sort by date
            transactions.sort(key=lambda t: t.date if hasattr(t, 'date') else t.created_at)
            return transactions
        return []

    def create_budget_item(
        self,
        period_id: int,
        payment_type: str,
        budgeted_cost: Decimal,
        allocation_strategy: str,
    ) -> BudgetItem:
        """Create a budget item for expense allocation.

        Args:
            period_id: Service period ID
            payment_type: Type of expense (e.g., "Water", "Electric")
            budgeted_cost: Budgeted amount for this type
            allocation_strategy: Strategy for allocation (PROPORTIONAL, FIXED_FEE, USAGE_BASED, NONE)

        Returns:
            Created BudgetItem object

        Raises:
            ValueError: If period not found, amount invalid, or invalid strategy
        """
        if self.db:
            # Validate period exists
            period = self.db.query(ServicePeriod).filter_by(id=period_id).first()
            if not period:
                raise ValueError(f"Period {period_id} not found")

            # Validate amount
            if budgeted_cost <= Decimal(0):
                raise ValueError("Budgeted cost must be positive")

            # Validate strategy
            valid_strategies = ["PROPORTIONAL", "FIXED_FEE", "USAGE_BASED", "NONE"]
            if allocation_strategy not in valid_strategies:
                raise ValueError(f"Invalid strategy. Must be one of: {', '.join(valid_strategies)}")

            budget_item = BudgetItem(
                service_period_id=period_id,
                payment_type=payment_type,
                budgeted_cost=budgeted_cost,
                allocation_strategy=allocation_strategy,
            )
            self.db.add(budget_item)
            self.db.commit()
            self.db.refresh(budget_item)
            return budget_item
        return None

    def get_budget_items(self, period_id: int) -> List[BudgetItem]:
        """Get all budget items for a period.

        Args:
            period_id: Period ID

        Returns:
            List of BudgetItem objects
        """
        if self.db:
            return (
                self.db.query(BudgetItem)
                .filter_by(service_period_id=period_id)
                .all()
            )
        return []

    def get_budget_item(self, budget_item_id: int) -> Optional[BudgetItem]:
        """Get a specific budget item by ID.

        Args:
            budget_item_id: Budget item ID

        Returns:
            BudgetItem object or None if not found
        """
        if self.db:
            return self.db.query(BudgetItem).filter_by(id=budget_item_id).first()
        return None

    def update_budget_item(
        self,
        budget_item_id: int,
        budgeted_cost: Optional[Decimal] = None,
        allocation_strategy: Optional[str] = None,
    ) -> BudgetItem:
        """Update a budget item.

        Args:
            budget_item_id: Budget item ID
            budgeted_cost: New cost (optional)
            allocation_strategy: New strategy (optional)

        Returns:
            Updated BudgetItem object

        Raises:
            ValueError: If item not found or invalid data
        """
        if self.db:
            budget_item = self.db.query(BudgetItem).filter_by(id=budget_item_id).first()
            if not budget_item:
                raise ValueError(f"Budget item {budget_item_id} not found")

            if budgeted_cost is not None:
                if budgeted_cost <= Decimal(0):
                    raise ValueError("Budgeted cost must be positive")
                budget_item.budgeted_cost = budgeted_cost

            if allocation_strategy is not None:
                valid_strategies = ["PROPORTIONAL", "FIXED_FEE", "USAGE_BASED", "NONE"]
                if allocation_strategy not in valid_strategies:
                    raise ValueError(f"Invalid strategy. Must be one of: {', '.join(valid_strategies)}")
                budget_item.allocation_strategy = allocation_strategy

            self.db.commit()
            self.db.refresh(budget_item)
            return budget_item
        return None

    def record_meter_reading(
        self,
        period_id: int,
        meter_name: str,
        meter_start_reading: Decimal,
        meter_end_reading: Decimal,
        calculated_total_cost: Decimal,
        unit: str = None,
        description: str = None,
    ) -> Optional[UtilityReading]:
        """Record a meter reading for usage-based billing.

        Args:
            period_id: Service period ID
            meter_name: Meter identifier (e.g., "Water Meter A")
            meter_start_reading: Starting meter reading (Decimal)
            meter_end_reading: Ending meter reading (Decimal)
            calculated_total_cost: Total cost for consumption (must be positive)
            unit: Unit of measurement (e.g., "m³", "kWh")
            description: Optional notes

        Returns:
            Created UtilityReading object

        Raises:
            ValueError: If period not found or cost is invalid
        """
        if self.db:
            # Validate period exists
            period = self.db.query(ServicePeriod).filter_by(id=period_id).first()
            if not period:
                raise ValueError(f"Period {period_id} not found")

            # Validate cost is non-negative
            if calculated_total_cost < Decimal(0):
                raise ValueError("Calculated total cost must be non-negative")

            reading = UtilityReading(
                service_period_id=period_id,
                meter_name=meter_name,
                meter_start_reading=meter_start_reading,
                meter_end_reading=meter_end_reading,
                calculated_total_cost=calculated_total_cost,
                unit=unit,
                description=description,
                recorded_at=datetime.now(),
            )
            self.db.add(reading)
            self.db.commit()
            self.db.refresh(reading)
            return reading
        return None

    def get_meter_readings(self, period_id: int) -> List[UtilityReading]:
        """Get all meter readings for a period.

        Args:
            period_id: Service period ID

        Returns:
            List of UtilityReading objects
        """
        if self.db:
            return (
                self.db.query(UtilityReading)
                .filter_by(service_period_id=period_id)
                .all()
            )
        return []

    def get_meter_reading(self, reading_id: int) -> Optional[UtilityReading]:
        """Get a specific meter reading by ID.

        Args:
            reading_id: Meter reading ID

        Returns:
            UtilityReading object or None if not found
        """
        if self.db:
            return self.db.query(UtilityReading).filter_by(id=reading_id).first()
        return None

    def calculate_consumption(
        self,
        start_reading: Decimal,
        end_reading: Decimal,
    ) -> Decimal:
        """Calculate consumption from meter readings.

        Args:
            start_reading: Starting meter reading
            end_reading: Ending meter reading

        Returns:
            Consumption (end_reading - start_reading)
        """
        return end_reading - start_reading
