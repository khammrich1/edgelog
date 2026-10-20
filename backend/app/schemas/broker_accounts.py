"""Schemas for the broker-account ownership registry (issue #95).

`verification_status` is included in every read response so a caller can
never mistake an unverified claim for a certified one -- there is no
endpoint anywhere in this slice that can ever produce "verified"; see
app/models/broker_accounts.py for why.

Normalization policy (owner review, PR #98): `provider` and `account_id`
are free-text as typed by the trader, but the uniqueness key must not be
bypassable by case or whitespace alone -- "TopstepX" and "topstepx" must
collide as the same registration, not silently create two rows for the
same real account. `provider` is a small, known set of broker-namespace
strings (mirrors agent/'s own provider naming, e.g. "topstepx"), so it is
canonicalized to lowercase. `account_id` is an opaque broker-assigned
identifier whose casing may be meaningful for some future provider, so
it is only whitespace-trimmed, never case-folded."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

VerificationStatus = Literal["unverified", "verified"]


class BrokerAccountCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=50)
    account_id: str = Field(min_length=1, max_length=100)
    label: Optional[str] = Field(default=None, max_length=200)

    @field_validator("provider")
    @classmethod
    def _normalize_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("provider must not be blank")
        return normalized

    @field_validator("account_id")
    @classmethod
    def _normalize_account_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("account_id must not be blank")
        return normalized


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
