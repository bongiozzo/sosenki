"""TelegramUserCandidate model - pending user requests."""

from sqlalchemy import Column, BigInteger, String, Enum as SQLEnum, UniqueConstraint
import enum

from backend.app.models.base import BaseModel


class CandidateStatus(str, enum.Enum):
    """Status of a pending request."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class TelegramUserCandidate(BaseModel):
    """Lightweight record for a user requesting access via Telegram."""

    __tablename__ = "telegram_user_candidate"

    telegram_id = Column(BigInteger, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    note = Column(String(1024), nullable=True)

    status = Column(SQLEnum(CandidateStatus), default=CandidateStatus.PENDING, nullable=False)

    __table_args__ = (UniqueConstraint("telegram_id", name="uq_candidate_telegram_id"),)
