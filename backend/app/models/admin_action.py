"""AdminAction model - audit log for admin decisions."""

from sqlalchemy import Column, Integer, ForeignKey, String
import enum

from backend.app.models.base import BaseModel


class AdminActionType(str, enum.Enum):
    """Type of admin action."""

    ACCEPT = "accept"
    REJECT = "reject"


class AdminAction(BaseModel):
    """Audit log for admin decisions on user requests."""

    __tablename__ = "admin_action"

    admin_id = Column(Integer, nullable=False)
    request_id = Column(Integer, ForeignKey("telegram_user_candidate.id"), nullable=False)
    action = Column(String(50), nullable=False)
    reason = Column(String(1000), nullable=True)

    # Relationships
    # request = relationship("TelegramUserCandidate")
    # admin_user = relationship("SOSenkiUser")
