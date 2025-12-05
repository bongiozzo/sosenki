"""Audit log model for tracking key entity lifecycle events."""

from typing import Any

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base, BaseModel


class AuditLog(Base, BaseModel):
    """Audit log entry for tracking changes to key entities.

    Minimal audit table tracking entity modifications (create, close).
    Records who (actor_id) did what (action) to which entity (entity_type, entity_id)
    and optional field snapshots (changes).
    """

    __tablename__ = "audit_logs"

    entity_type: Mapped[str] = mapped_column(index=False)
    """Entity type being audited: "period", "bill", etc."""

    entity_id: Mapped[int] = mapped_column(index=False)
    """Primary key of the entity being audited."""

    action: Mapped[str] = mapped_column(index=False)
    """Action performed: "create", "close", etc."""

    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=False)
    """User (admin) who performed the action. None for system actions."""

    changes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, index=False)
    """Optional JSON snapshot of changed fields: {"status": "closed", "bill_count": 5}."""

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, entity_type={self.entity_type}, entity_id={self.entity_id}, "
            f"action={self.action}, actor_id={self.actor_id}, created_at={self.created_at})>"
        )


__all__ = ["AuditLog"]
