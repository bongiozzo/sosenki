"""SOSenkiUser model - main user entity."""

from sqlalchemy import Column, BigInteger, String, UniqueConstraint, JSON

from backend.app.models.base import BaseModel


class SOSenkiUser(BaseModel):
    """Main user model linked to SOSenki application."""

    __tablename__ = "sosenki_user"

    username = Column(String(255), nullable=True, unique=True)
    email = Column(String(255), nullable=True)
    telegram_id = Column(BigInteger, nullable=False, unique=True, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)

    # Roles: "Administrator", "Tenant", "Owner", "Investor", "User"
    # Use JSON for SQLite compatibility, will use ARRAY for PostgreSQL
    roles = Column(JSON, default=["User"], nullable=False)

    # Profile fields
    avatar_url = Column(String(512), nullable=True)
    bio = Column(String(1000), nullable=True)

    __table_args__ = (UniqueConstraint("telegram_id", name="uq_sosenki_user_telegram_id"),)

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in (self.roles or [])

    def is_admin(self) -> bool:
        """Check if user is an administrator."""
        return self.has_role("Administrator")
