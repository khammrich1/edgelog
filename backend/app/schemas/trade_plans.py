"""Pre-trade plan schemas (issue #59)."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

Direction = Literal["long", "short"]
PlanStatus = Literal["pending", "approved", "rejected", "expired", "invalidated", "canceled"]

# Terminal: a status a plan can never leave once reached.
TERMINAL_STATUSES = {"approved", "rejected", "expired", "invalidated", "canceled"}


class TradePlanCreate(BaseModel):
    # Reuses the broker-accounts registry (issue #95) instead of a
    # free-text account field. Optional: a trader who hasn't registered
    # an account yet can still create and review a plan.
    broker_account_id: Optional[int] = None
    symbol: str = Field(min_length=1, max_length=20)
    direction: Direction
    entry_price: Decimal = Field(gt=0)
    stop_price: Decimal = Field(gt=0)
    target_price: Optional[Decimal] = Field(default=None, gt=0)
    quantity: int = Field(gt=0)
    max_risk_dollars: Optional[Decimal] = Field(default=None, gt=0)
    setup: Optional[str] = Field(default=None, max_length=200)
    invalidation_condition: Optional[str] = Field(default=None, max_length=4000)
    rationale: Optional[str] = Field(default=None, max_length=4000)
    expires_at: datetime

    @field_validator("expires_at")
    @classmethod
    def _assume_utc_if_naive(cls, value: datetime) -> datetime:
        """A naive datetime (no UTC offset -- e.g. from a plain API client,
        not this repo's own frontend, which always sends .toISOString())
        would otherwise raise an unhandled TypeError the moment it's
        compared against datetime.now(timezone.utc) in the route layer,
        surfacing as a 500 instead of a clean validation result. Treating
        it as UTC (rather than rejecting it) matches the server's own
        clock convention used everywhere else in this module."""
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @model_validator(mode="after")
    def _require_valid_price_ordering(self) -> "TradePlanCreate":
        if self.direction == "long":
            if self.stop_price >= self.entry_price:
                raise ValueError("For a long plan, stop_price must be below entry_price")
            if self.target_price is not None and self.target_price <= self.entry_price:
                raise ValueError("For a long plan, target_price must be above entry_price")
        else:
            if self.stop_price <= self.entry_price:
                raise ValueError("For a short plan, stop_price must be above entry_price")
            if self.target_price is not None and self.target_price >= self.entry_price:
                raise ValueError("For a short plan, target_price must be below entry_price")
        return self


class TradePlanDecision(BaseModel):
    """Body for approve/reject/invalidate/cancel -- the only fields a
    trader can ever supply after a plan already exists. There is no update
    endpoint for a plan's content fields; see TradePlanCreate's docstring
    and revise_trade_plan for why that's a new row, not an edit."""

    decision_note: Optional[str] = Field(default=None, max_length=4000)


class TradePlanRead(BaseModel):
    id: int
    previous_version_id: Optional[int]
    revision_number: int
    is_latest_revision: bool
    """False when a newer revision has since been created from this plan
    (see revise_trade_plan). This plan's own status/decided_at/decision_note
    are never rewritten when that happens -- only this flag changes."""
    broker_account_id: Optional[int]
    """The live FK -- goes null if the linked broker_accounts row is later
    deleted (ondelete=SET NULL). The three fields below do NOT depend on
    this still resolving: they are a snapshot taken once at creation, so
    an approved (or any) plan's account identity survives the registry
    row being edited or deleted afterward (owner review, PR #101)."""
    broker_account_label: Optional[str]
    broker_account_provider: Optional[str]
    broker_account_account_id: Optional[str]
    """Snapshotted from the broker_accounts row at the moment this plan
    (or revision) was created. All three are null if no account was
    linked at creation; otherwise they stay exactly as they were then,
    even if that registry row is later relabeled or deleted."""
    symbol: str
    direction: Direction
    entry_price: Decimal
    stop_price: Decimal
    target_price: Optional[Decimal]
    quantity: int
    max_risk_dollars: Optional[Decimal]
    setup: Optional[str]
    invalidation_condition: Optional[str]
    rationale: Optional[str]
    expires_at: datetime
    status: PlanStatus
    decided_at: Optional[datetime]
    decision_note: Optional[str]
    created_at: datetime
    # Derived risk/reward -- computed fresh from the immutable
    # entry/stop/target/quantity every time, never stored, so it can never
    # drift from those fields.
    risk_points: Decimal
    risk_dollars: Optional[Decimal]
    """None when the symbol has no verified instrument multiplier -- never
    a fabricated number. See app.core.instruments.get_multiplier."""
    reward_points: Optional[Decimal]
    reward_dollars: Optional[Decimal]
    reward_risk_ratio: Optional[Decimal]
    multiplier_known: bool
    exceeds_max_risk: Optional[bool]
    """True if risk_dollars is known and exceeds the trader's own declared
    max_risk_dollars. None if either figure is unknown/not set."""

    model_config = {"from_attributes": False}
