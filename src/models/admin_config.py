"""Administrator ORM model for managing approved admins."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class Administrator(Base):
    """Model for storing administrator configuration and metadata."""

    __tablename__ = "administrators"

    # Primary key: Telegram ID (unique per admin)
    telegram_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Optional: human-readable name
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Active status (soft-delete pattern)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
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

    def __repr__(self) -> str:
        return (
            f"<Administrator(telegram_id={self.telegram_id}, name={self.name}, "
            f"active={self.active})>"
        )


__all__ = ["Administrator"]
