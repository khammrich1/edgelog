"""AI screenshot trade capture schemas (VS3): extraction only, never persisted directly."""
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.schemas.trades import Direction


class ScreenshotTradeExtraction(BaseModel):
    symbol: Optional[str] = None
    direction: Optional[Direction] = None
    entry_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    target_price: Optional[Decimal] = None
    initial_quantity: Optional[int] = None
    notes: Optional[str] = None
