"""Service period management service for database operations."""

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from src.models.account import Account
from src.models.bill import Bill, BillType
from src.models.service_period import ServicePeriod
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


@dataclass
class PeriodDefaults:
    """Previous period values for form defaults."""

    electricity_end: str | None = None
    electricity_multiplier: str | None = None
    electricity_rate: str | None = None
    electricity_losses: str | None = None


class ServicePeriodService:
    """Service for service period database operations.

    Encapsulates all ServicePeriod and related Bill CRUD operations.
    Used by bot handlers to interact with periods without direct database access.
    """

    def __init__(self, db_session: Session):
        """Initialize with database session."""
        self.db = db_session

    def get_open_periods(self, limit: int = 5) -> list[ServicePeriod]:
        """Get open service periods ordered by start_date desc.

        Args:
            limit: Maximum number of periods to return

        Returns:
            List of open ServicePeriod objects
        """
        return (
            self.db.query(ServicePeriod)
            .filter(ServicePeriod.status == "open")
            .order_by(ServicePeriod.start_date.desc())
            .limit(limit)
            .all()
        )

    def get_by_id(self, period_id: int) -> ServicePeriod | None:
        """Get service period by ID.

        Args:
            period_id: Period ID to fetch

        Returns:
            ServicePeriod if found, None otherwise
        """
        return self.db.query(ServicePeriod).filter(ServicePeriod.id == period_id).first()

    def get_latest_period(self) -> ServicePeriod | None:
        """Get most recent period by end_date.

        Used for suggesting default start date for new periods.

        Returns:
            Most recent ServicePeriod or None if no periods exist
        """
        return self.db.query(ServicePeriod).order_by(ServicePeriod.end_date.desc()).first()

    def get_previous_period(self, current_start_date: date) -> ServicePeriod | None:
        """Get period where end_date equals given start_date.

        Used for fetching default electricity values from previous period.

        Args:
            current_start_date: Start date of current period

        Returns:
            Previous ServicePeriod or None if not found
        """
        return (
            self.db.query(ServicePeriod)
            .filter(ServicePeriod.end_date == current_start_date)
            .first()
        )

    def get_previous_period_defaults(self, current_start_date: date) -> PeriodDefaults:
        """Get electricity defaults from previous period.

        Args:
            current_start_date: Start date of current period

        Returns:
            PeriodDefaults with previous period electricity values
        """
        previous_period = self.get_previous_period(current_start_date)
        if not previous_period:
            return PeriodDefaults()

        return PeriodDefaults(
            electricity_end=(
                str(previous_period.electricity_end) if previous_period.electricity_end else None
            ),
            electricity_multiplier=(
                str(previous_period.electricity_multiplier)
                if previous_period.electricity_multiplier
                else None
            ),
            electricity_rate=(
                str(previous_period.electricity_rate) if previous_period.electricity_rate else None
            ),
            electricity_losses=(
                str(previous_period.electricity_losses)
                if previous_period.electricity_losses
                else None
            ),
        )

    def list_periods(self, limit: int = 10) -> list[ServicePeriod]:
        """List all periods ordered by start_date desc.

        Args:
            limit: Maximum number of periods to return

        Returns:
            List of ServicePeriod objects
        """
        return (
            self.db.query(ServicePeriod)
            .order_by(ServicePeriod.start_date.desc())
            .limit(limit)
            .all()
        )

    def create_period(self, start_date: date, end_date: date, actor_id: int | None = None) -> ServicePeriod:
        """Create new service period with auto-generated name.

        Name format: "DD.MM.YYYY - DD.MM.YYYY"
        Status: "open" by default

        Args:
            start_date: Period start date
            end_date: Period end date
            actor_id: Admin user ID who created the period (optional)

        Returns:
            Created ServicePeriod object
        """
        period_name = f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"

        new_period = ServicePeriod(
            name=period_name,
            start_date=start_date,
            end_date=end_date,
            status="open",
        )
        self.db.add(new_period)
        self.db.commit()

        logger.info(
            "Created new service period: id=%d, name=%s, dates=%s to %s",
            new_period.id,
            period_name,
            start_date,
            end_date,
        )

        # Audit log
        AuditService.log(self.db, "period", new_period.id, "create", actor_id)
        self.db.commit()

        return new_period

    def update_electricity_data(
        self,
        period_id: int,
        electricity_start: Decimal,
        electricity_end: Decimal,
        electricity_multiplier: Decimal,
        electricity_rate: Decimal,
        electricity_losses: Decimal,
        close_period: bool = True,
        actor_id: int | None = None,
    ) -> bool:
        """Update period with electricity readings and optionally close it.

        Args:
            period_id: Period ID to update
            electricity_start: Starting meter reading
            electricity_end: Ending meter reading
            electricity_multiplier: Consumption multiplier
            electricity_rate: Rate per kWh
            electricity_losses: Transmission losses ratio
            close_period: Whether to close the period after update
            actor_id: Admin user ID who closed the period (optional)

        Returns:
            True if successful, False if period not found
        """
        period = self.get_by_id(period_id)
        if not period:
            return False

        period.electricity_start = electricity_start
        period.electricity_end = electricity_end
        period.electricity_multiplier = electricity_multiplier
        period.electricity_rate = electricity_rate
        period.electricity_losses = electricity_losses

        if close_period:
            period.status = "closed"

        self.db.commit()

        logger.info(
            "Updated period %d electricity data: start=%s, end=%s, multiplier=%s, rate=%s, losses=%s, closed=%s",
            period_id,
            electricity_start,
            electricity_end,
            electricity_multiplier,
            electricity_rate,
            electricity_losses,
            close_period,
        )

        # Audit log for period close
        if close_period:
            AuditService.log(self.db, "period", period_id, "close", actor_id, {"status": "closed"})
            self.db.commit()

        return True

    def create_shared_electricity_bills(
        self,
        period_id: int,
        owner_shares: list,
        actor_id: int | None = None,
    ) -> int:
        """Create SHARED_ELECTRICITY bills for each owner.

        Looks up owner's account and creates Bill record.

        Args:
            period_id: Service period ID
            owner_shares: List of OwnerShare namedtuples with user_id and calculated_bill_amount
            actor_id: Admin user ID who created bills (optional)

        Returns:
            Count of bills created
        """
        bills_created = 0

        for share in owner_shares:
            # Find account for this user
            account = (
                self.db.query(Account)
                .filter(Account.user_id == share.user_id, Account.account_type == "owner")
                .first()
            )

            if account:
                bill = Bill(
                    service_period_id=period_id,
                    account_id=account.id,
                    property_id=None,
                    bill_type=BillType.SHARED_ELECTRICITY,
                    bill_amount=share.calculated_bill_amount,
                )
                self.db.add(bill)
                bills_created += 1

        self.db.commit()

        logger.info(
            "Created %d shared electricity bills for period %d",
            bills_created,
            period_id,
        )

        # Audit log for bills batch creation
        if bills_created > 0:
            AuditService.log(
                self.db,
                "bill",
                period_id,
                "create",
                actor_id,
                {"bill_type": "SHARED_ELECTRICITY", "count": bills_created},
            )
            self.db.commit()

        return bills_created


__all__ = ["ServicePeriodService", "PeriodDefaults"]
