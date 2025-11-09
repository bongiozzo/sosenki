"""SQLAlchemy base model with common fields and model exports."""

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

# Base class for all models
Base = declarative_base()


class BaseModel:
    """Base model with common timestamp fields."""

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# Import models to register them with Base (after Base is defined)
# This must be after Base declaration to avoid circular imports
from src.models.user import User  # noqa: E402
from src.models.access_request import AccessRequest, RequestStatus  # noqa: E402

# Financial/Payment models
from src.models.payment.service_period import ServicePeriod, PeriodStatus  # noqa: E402
from src.models.payment.contribution_ledger import ContributionLedger  # noqa: E402
from src.models.payment.expense_ledger import ExpenseLedger  # noqa: E402
from src.models.payment.budget_item import BudgetItem, AllocationStrategy  # noqa: E402
from src.models.payment.utility_reading import UtilityReading  # noqa: E402
from src.models.payment.service_charge import ServiceCharge  # noqa: E402

__all__ = [
    "Base",
    "BaseModel",
    "User",
    "AccessRequest",
    "RequestStatus",
    "ServicePeriod",
    "PeriodStatus",
    "ContributionLedger",
    "ExpenseLedger",
    "BudgetItem",
    "AllocationStrategy",
    "UtilityReading",
    "ServiceCharge",
]

