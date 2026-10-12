"""AI screenshot trade capture schemas (VS3): extraction only, never persisted directly."""
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.trades import Direction


class ScreenshotTradeExtraction(BaseModel):
    symbol: Optional[str] = None
    direction: Optional[Direction] = None
    entry_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    target_price: Optional[Decimal] = None
    initial_quantity: Optional[int] = None
    notes: Optional[str] = None
    # Issue #64: every value above is an unverified suggestion, never a
    # broker-confirmed fill. tick_warnings flags prices that aren't aligned
    # to the instrument's known tick size (a common signature of a misread
    # digit) so the client can surface them instead of silently trusting
    # them. An empty list means "nothing flagged", not "confirmed correct" --
    # EdgeLog has no way to verify these numbers against the real source.
    tick_warnings: list[str] = Field(default_factory=list)
