"""Trade lifecycle schemas (VS3)."""
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

Direction = Literal["long", "short"]
TradeStatus = Literal["open", "closed", "canceled"]


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
    setup: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=4000)


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
    created_at: datetime
    updated_at: datetime
