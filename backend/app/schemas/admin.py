"""Admin page schemas: account roster, site traffic, and feedback."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AccountRosterEntry(BaseModel):
    id: int
    email: str
    is_admin: bool
    created_at: datetime
    last_activity_at: Optional[datetime] = None
    last_activity_path: Optional[str] = None


class TrafficRow(BaseModel):
    path: str
    hits: int
    unique_auth_users: int
    auth_hits: int
    unauth_hits: int


class FeedbackEntry(BaseModel):
    id: int
    user_email: Optional[str] = None
    message: str
    created_at: datetime


class FeedbackCreate(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class PageViewCreate(BaseModel):
    path: str = Field(min_length=1, max_length=500)
