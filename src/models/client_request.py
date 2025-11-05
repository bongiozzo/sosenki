"""ClientRequest ORM model for tracking client access requests."""

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base, BaseModel


class RequestStatus(PyEnum):
    """Enumeration for request status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ClientRequest(Base, BaseModel):
    """Model for storing client access requests with approval status and timeline."""

    __tablename__ = "client_requests"

    # Core request fields
    client_telegram_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    request_message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus, native_enum=False),
        default=RequestStatus.PENDING,
        nullable=False,
        index=True,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Admin response fields (nullable if pending)
    admin_telegram_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    admin_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Constraints
    __table_args__ = (
        # Index for status queries
        Index("idx_status", "status"),
        # Index for submitted_at timeline queries
        Index("idx_submitted_at", "submitted_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ClientRequest(id={self.id}, client_telegram_id={self.client_telegram_id}, "
            f"status={self.status.value}, submitted_at={self.submitted_at})>"
        )


__all__ = ["ClientRequest", "RequestStatus"]
