"""Audit service for logging entity lifecycle events."""

from sqlalchemy.orm import Session

from src.models.audit_log import AuditLog


class AuditService:
    """Service for audit log operations.

    Provides static method to create minimal audit log entries.
    """

    @staticmethod
    def log(
        db: Session,
        entity_type: str,
        entity_id: int,
        action: str,
        actor_id: int | None = None,
        changes: dict | None = None,
    ) -> AuditLog:
        """Create audit log entry (one-liner).

        Args:
            db: Database session
            entity_type: Type of entity ("period", "bill", etc.)
            entity_id: Primary key of the entity
            action: Action performed ("create", "close", etc.)
            actor_id: User (admin) who performed the action (optional)
            changes: Optional JSON snapshot of changed fields

        Returns:
            Created AuditLog object
        """
        audit = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_id=actor_id,
            changes=changes,
        )
        db.add(audit)
        return audit


__all__ = ["AuditService"]
