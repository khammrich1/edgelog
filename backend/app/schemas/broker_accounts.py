"""Schemas for the broker-account ownership registry (issue #95).

`verification_status` is included in every read response so a caller can
never mistake an unverified claim for a certified one -- there is no
endpoint anywhere in this slice that can ever produce "verified"; see
app/models/broker_accounts.py for why."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

VerificationStatus = Literal["unverified", "verified"]


class BrokerAccountCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=50)
    account_id: str = Field(min_length=1, max_length=100)
    label: Optional[str] = Field(default=None, max_length=200)


class BrokerAccountRead(BaseModel):
    id: int
    provider: str
    account_id: str
    label: Optional[str]
    verification_status: VerificationStatus
    """Always "unverified" today -- no code path in this slice ever sets
    this to "verified". See issue #95 for what a real check would need."""
    verified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
