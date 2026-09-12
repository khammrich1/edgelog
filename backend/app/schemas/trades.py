"""Trade lifecycle schemas (VS3)."""
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

Direction = Literal["long", "short"]
TradeStatus = Literal["open", "closed"]


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


class TradeRead(BaseModel):
    id: int
    trading_day_id: int
    symbol: str
    direction: Direction
    entry_price: Decimal
    initial_quantity: int
    entry_time: datetime
    stop_price: Optional[Decimal]
    target_price: Optional[Decimal]
    setup: Optional[str]
    notes: Optional[str]
    status: TradeStatus
    remaining_quantity: int
    exits: list[TradeExitRead]
    realized_points: Decimal
    realized_pnl: Optional[Decimal]
    planned_risk_points: Optional[Decimal]
    planned_risk_dollars: Optional[Decimal]
    multiplier_known: bool
    created_at: datetime
    updated_at: datetime
