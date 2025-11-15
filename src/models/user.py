"""User ORM model with unified role-based access control."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base, BaseModel


class User(Base, BaseModel):
    """
    Unified user model representing any person in the system.

    Users can hold multiple roles simultaneously via independent boolean flags:
    - is_active: PRIMARY gate for Mini App access (all users)
    - is_investor: Can access Invest features (requires is_active=True)
    - is_administrator: Can approve/reject access requests
    - is_owner: User is a property owner
    - is_stakeholder: Owner's legal contract status (True=signed, False=unsigned; only valid when is_owner=True)
    - is_staff: Can view analytics and support users (future)
    - is_tenant: User has rental contract with owner for specified period

    This design supports flexible role assignment without schema changes.
    """

    __tablename__ = "users"

    # Identity fields
    telegram_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Primary identifier from Telegram (nullable until user becomes active)",
    )
    username: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True, comment="Telegram username"
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="Full name (first and last name combined) - unique identifier",
    )

    # Role flags (independent - user can have multiple roles)
    is_investor: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Can access Invest features (requires is_active=True)",
    )
    is_administrator: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Can approve/reject access requests"
    )
    is_owner: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="User is a property owner"
    )
    is_staff: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Can view analytics and support users (future)",
    )

    # Stakeholder status (only meaningful when is_owner=True)
    is_stakeholder: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Owner's contract status: True=signed legal contract, False=not yet signed. Only valid when is_owner=True",
    )

    # Tenant status
    is_tenant: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="User has rental contract with property owner for specified period",
    )

    # Primary access gate
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="PRIMARY Mini App access gate - can access Mini App if True",
    )

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

    # Indexes for common queries
    __table_args__ = (
        Index("idx_telegram_id", "telegram_id"),
        Index("idx_username", "username"),
        Index("idx_is_active", "is_active"),
        Index("idx_investor_active", "is_investor", "is_active"),
        Index("idx_name_unique", "name", unique=True),
    )

    # Relationships
    properties: Mapped[list["Property"]] = relationship(  # noqa: F821
        "Property",
        back_populates="owner",
        foreign_keys="Property.owner_id",
    )
    payments: Mapped[list["Payment"]] = relationship(  # noqa: F821
        "Payment",
        back_populates="owner",
        foreign_keys="Payment.owner_id",
    )

    def __repr__(self) -> str:
        roles = []
        if self.is_investor:
            roles.append("investor")
        if self.is_administrator:
            roles.append("admin")
        if self.is_owner:
            roles.append("owner")
        if self.is_staff:
            roles.append("staff")
        if self.is_tenant:
            roles.append("tenant")
        role_str = ",".join(roles) if roles else "none"

        return (
            f"<User(id={self.id}, name={self.name}, telegram_id={self.telegram_id}, "
            f"is_active={self.is_active}, roles=[{role_str}])>"
        )


__all__ = ["User"]
