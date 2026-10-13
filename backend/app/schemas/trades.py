"""Trade lifecycle schemas (VS3)."""
from datetime import date as date_type, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

Direction = Literal["long", "short"]
TradeStatus = Literal["open", "closed", "canceled"]
PriceSource = Literal["manual", "image_extracted"]
RuleAdherence = Literal["yes", "no", "unknown"]


class TradeExitCreate(BaseModel):
    quantity: int = Field(gt=0)
    exit_price: Decimal = Field(gt=0)
    exit_time: datetime


class TradeExitUpdate(BaseModel):
    quantity: Optional[int] = Field(default=None, gt=0)
    exit_price: Optional[Decimal] = Field(default=None, gt=0)
    exit_time: Optional[datetime] = None


class TradeExitRead(BaseModel):
    id: int
    quantity: int
    exit_price: Decimal
    exit_time: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class TradeEntryCreate(BaseModel):
    """An additional entry leg (scale-in), beyond the trade's original entry."""

    quantity: int = Field(gt=0)
    entry_price: Decimal = Field(gt=0)
    entry_time: datetime


class TradeEntryRead(BaseModel):
    id: int
    quantity: int
    entry_price: Decimal
    entry_time: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class TradeCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    direction: Direction
    entry_price: Decimal = Field(gt=0)
    initial_quantity: int = Field(gt=0)
    entry_time: datetime
    stop_price: Optional[Decimal] = Field(default=None, gt=0)
    target_price: Optional[Decimal] = Field(default=None, gt=0)
    # Required as of the P1 refinement: a trade must be classified against
    # a setup at the moment it's logged, since setups are becoming a
    # first-class concept trades will eventually be graded against (Trade
    # Ranker, issue #32). TradeUpdate.setup stays optional -- editing an
    # existing trade must not force a re-classification -- and TradeRead
    # keeps setup Optional so trades logged before this requirement still
    # load and render.
    setup: str = Field(min_length=1, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=4000)
    # Issue #64: set by the client when entry/stop/target/quantity were
    # prefilled from AI screenshot extraction and the trader confirmed them
    # (edited or not) before submitting. extraction_snapshot/extracted_at
    # are required together with price_source="image_extracted" so there's
    # always an immutable record of exactly what was extracted, distinct
    # from whatever the trader actually submitted.
    price_source: PriceSource = "manual"
    extraction_snapshot: Optional[dict] = None
    extracted_at: Optional[datetime] = None
    # Plan (DF-VS1, issue #78): the trader's original intended stop/target
    # and rationale, captured only at creation -- see TradeUpdate, which
    # deliberately excludes these so the plan can never be rewritten.
    # planned_quantity isn't accepted here -- the server always snapshots
    # it from initial_quantity below, so it can't be submitted out of sync.
    planned_stop_price: Optional[Decimal] = Field(default=None, gt=0)
    planned_target_price: Optional[Decimal] = Field(default=None, gt=0)
    plan_rationale: Optional[str] = Field(default=None, max_length=4000)
    # Write-only: tells the server to stamp plan_verified_at from its own
    # clock, affirming this plan was recorded before execution. The server
    # timestamp is the only thing that ever sets plan_verified_at -- a
    # trader can never backdate or directly supply it, so a retrospective
    # entry can never be mislabeled as verified pre-trade evidence.
    plan_verified: bool = False

    @model_validator(mode="after")
    def _require_snapshot_for_extracted(self) -> "TradeCreate":
        if self.price_source == "image_extracted" and (
            self.extraction_snapshot is None or self.extracted_at is None
        ):
            raise ValueError(
                "extraction_snapshot and extracted_at are required when price_source is image_extracted"
            )
        return self


class TradeUpdate(BaseModel):
    symbol: Optional[str] = Field(default=None, min_length=1, max_length=20)
    direction: Optional[Direction] = None
    entry_price: Optional[Decimal] = Field(default=None, gt=0)
    initial_quantity: Optional[int] = Field(default=None, gt=0)
    entry_time: Optional[datetime] = None
    stop_price: Optional[Decimal] = Field(default=None, gt=0)
    target_price: Optional[Decimal] = Field(default=None, gt=0)
    setup: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=4000)
    # Outcome (DF-VS1): judged after the fact, so these stay editable here.
    # Deliberately NOT included: planned_stop_price, planned_target_price,
    # planned_quantity, plan_rationale, plan_verified_at -- the plan is set
    # once at creation (TradeCreate) and is never editable through this
    # schema, so it can never be silently rewritten by a later trade edit.
    rule_adherence: Optional[RuleAdherence] = None
    rule_adherence_note: Optional[str] = Field(default=None, max_length=4000)
    reflection_notes: Optional[str] = Field(default=None, max_length=4000)


class TradeSetupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class TradeSetupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class TradeSetupRead(BaseModel):
    id: int
    name: str
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class TradeRead(BaseModel):
    id: int
    trading_day_id: int
    symbol: str
    direction: Direction
    entry_price: Decimal
    """The original entry leg's price. See average_entry_price for the
    weighted-average price used in P&L/risk math once scale-in entries exist."""
    initial_quantity: int
    """The original entry leg's quantity. See total_quantity for the sum
    across the original entry plus any scale-ins."""
    entry_time: datetime
    stop_price: Optional[Decimal]
    target_price: Optional[Decimal]
    setup: Optional[str]
    notes: Optional[str]
    status: TradeStatus
    canceled_at: Optional[datetime]
    remaining_quantity: int
    total_quantity: int
    average_entry_price: Decimal
    entries: list[TradeEntryRead]
    exits: list[TradeExitRead]
    realized_points: Decimal
    realized_pnl: Optional[Decimal]
    planned_risk_points: Optional[Decimal]
    """Risk computed from the trade's CURRENT stop/target -- unchanged
    behavior, recalculates if the stop is moved. See original_planned_risk_*
    for the immutable at-entry figure."""
    planned_risk_dollars: Optional[Decimal]
    original_planned_risk_points: Optional[Decimal]
    """Risk computed from the immutable planned_stop_price/planned_quantity
    snapshot, if one was recorded at creation. Never recalculates when the
    live stop_price is later moved, so it answers "what was the plan"
    distinctly from planned_risk_points' "what is the risk now"."""
    original_planned_risk_dollars: Optional[Decimal]
    multiplier_known: bool
    has_screenshot: bool
    price_source: PriceSource
    extraction_snapshot: Optional[dict]
    """The original AI-extracted values at creation time, verbatim and
    immutable. Only present when price_source is image_extracted."""
    extracted_at: Optional[datetime]
    price_edited_after_extraction: bool
    """True once any of entry/stop/target/quantity has been changed since
    an image_extracted trade was created -- lets the UI show "edited since
    extraction" without needing to diff against extraction_snapshot itself."""
    # Plan (DF-VS1): set once at creation, immutable thereafter.
    planned_stop_price: Optional[Decimal]
    planned_target_price: Optional[Decimal]
    planned_quantity: Optional[int]
    plan_rationale: Optional[str]
    plan_verified_at: Optional[datetime]
    """Set by the server, only when the trader affirmed at creation that
    this plan was recorded before execution. Null means the trade's plan
    fields (if any) are retrospective/unverified, never to be treated as
    pre-trade evidence."""
    # Outcome (DF-VS1): editable after the fact via TradeUpdate.
    rule_adherence: Optional[RuleAdherence]
    rule_adherence_note: Optional[str]
    reflection_notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class TradeCalendarDay(BaseModel):
    """One day's trades for the Trade Calendar range endpoint (VS4). Only
    dates with at least one trade appear in the response list -- the caller
    already knows the full date range it asked for and treats an absent
    date as an empty day."""

    date: date_type
    trades: list[TradeRead]
