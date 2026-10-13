"""Trade lifecycle schemas (VS3)."""
from datetime import date as date_type, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

Direction = Literal["long", "short"]
TradeStatus = Literal["open", "closed", "canceled"]
PriceSource = Literal["manual", "image_extracted"]


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
    planned_risk_dollars: Optional[Decimal]
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
    created_at: datetime
    updated_at: datetime


class TradeCalendarDay(BaseModel):
    """One day's trades for the Trade Calendar range endpoint (VS4). Only
    dates with at least one trade appear in the response list -- the caller
    already knows the full date range it asked for and treats an absent
    date as an empty day."""

    date: date_type
    trades: list[TradeRead]
