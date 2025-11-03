"""Pydantic schemas for request submission (US2)."""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CreateRequestPayload(BaseModel):
    """Request payload for POST /requests."""

    telegram_id: int = Field(..., description="Telegram user ID")
    telegram_username: str | None = Field(None, description="Telegram username")
    first_name: str | None = Field(None, description="User's first name")
    last_name: str | None = Field(None, description="User's last name")
    phone: str | None = Field(None, description="User's phone number")
    email: str | None = Field(None, description="User's email address")
    note: str | None = Field(None, description="Request note/comment from user")

    model_config = ConfigDict(populate_by_name=True)


class RequestResponse(BaseModel):
    """Response schema for created request."""

    id: int
    telegram_id: int
    username: str | None = Field(None, serialization_alias="telegram_username")
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    note: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
