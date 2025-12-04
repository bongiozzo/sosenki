"""AccessRequest ORM model for tracking client access requests (audit log)."""

from enum import Enum as PyEnum

from sqlalchemy import Enum, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base, BaseModel


class RequestStatus(PyEnum):
    """Enumeration for request status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AccessRequest(Base, BaseModel):
    """
    Audit log for all access requests.

    This table serves as the complete history of approval workflows.
    Users are created with is_active=False; upon approval, is_active becomes True.

    Timestamps:
    - created_at: When request was created (request submitted)
    - updated_at: Last modified (when admin responded)
    """

    __tablename__ = "access_requests"

    # Core request fields
    user_telegram_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment="User's Telegram ID"
    )
    user_telegram_username: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="User's Telegram username (@username)"
    )
    request_message: Mapped[str] = mapped_column(
        Text, nullable=False, comment="User's request message"
    )
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus, native_enum=False),
        default=RequestStatus.PENDING,
        nullable=False,
        index=True,
        comment="Status: pending/approved/rejected",
    )

    # Admin response fields (nullable until admin responds)
    admin_telegram_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="Admin Telegram ID (who responded)",
    )
    admin_response: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Admin's response message"
    )

    # Standard ORM metadata timestamps (inherited from BaseModel)
    # created_at: When request was submitted
    # updated_at: When request was last updated (admin response time)

    # Indexes for common queries
    __table_args__ = (
        Index("idx_user_status", "user_telegram_id", "status"),
        Index("idx_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<AccessRequest(id={self.id}, user_telegram_id={self.user_telegram_id}, "
            f"status={self.status.value}, created_at={self.created_at})>"
        )


__all__ = ["AccessRequest", "RequestStatus"]
