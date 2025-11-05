"""AccessRequest ORM model for tracking client access requests (audit log)."""

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base, BaseModel


class RequestStatus(PyEnum):
    """Enumeration for request status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AccessRequest(Base, BaseModel):
    """
    Immutable audit log for all access requests.
    
    This table serves as the complete history of approval workflows.
    Users are created with is_active=False; upon approval, is_active becomes True.
    
    Renamed from ClientRequest for clarity (access request from any user).
    """

    __tablename__ = "access_requests"

    # Core request fields
    user_telegram_id: Mapped[str] = mapped_column(
        String(50), 
        ForeignKey("users.telegram_id"),
        nullable=False, 
        index=True,
        comment="User making the request"
    )
    request_message: Mapped[str] = mapped_column(
        Text, 
        nullable=False,
        comment="User's request message"
    )
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus, native_enum=False),
        default=RequestStatus.PENDING,
        nullable=False,
        index=True,
        comment="Current status: pending/approved/rejected"
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="When request was submitted"
    )

    # Admin response fields (nullable until admin responds)
    responded_by_admin_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("users.telegram_id"),
        nullable=True,
        index=True,
        comment="Admin who approved/rejected"
    )
    response_message: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="Admin's response message"
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        comment="When admin responded"
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_user_status", "user_telegram_id", "status"),
        Index("idx_status", "status"),
        Index("idx_submitted_at", "submitted_at"),
        Index("idx_responded_by", "responded_by_admin_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<AccessRequest(id={self.id}, user_telegram_id={self.user_telegram_id}, "
            f"status={self.status.value}, submitted_at={self.submitted_at})>"
        )


__all__ = ["AccessRequest", "RequestStatus"]
