"""Pydantic schemas for admin request handling (US3)."""

from datetime import datetime
from pydantic import BaseModel, Field


class AdminActionPayload(BaseModel):
    """Payload for POST /admin/requests/{request_id}/action."""

    action: str = Field(..., description="Action to perform: 'accept' or 'reject'")
    admin_id: int = Field(..., description="ID of the admin performing the action")
    reason: str | None = Field(None, description="Reason for rejection (optional)")


class AdminActionResponse(BaseModel):
    """Response for admin action."""

    id: int
    admin_id: int
    request_id: int
    action: str
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
