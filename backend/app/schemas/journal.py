"""Daily Journal schemas (VS2)."""
from datetime import date as date_type, datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChecklistItemCreate(BaseModel):
    label: str = Field(min_length=1, max_length=200)


class ChecklistItemUpdate(BaseModel):
    label: Optional[str] = Field(default=None, min_length=1, max_length=200)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ChecklistItemRead(BaseModel):
    id: int
    label: str
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class ChecklistCompletionRead(BaseModel):
    checklist_item_id: int
    label: str
    completed: bool


class ChecklistCompletionUpdate(BaseModel):
    completed: bool


class TradingDayUpdate(BaseModel):
    sleep_quality: Optional[int] = Field(default=None, ge=1, le=5)
    mood: Optional[int] = Field(default=None, ge=1, le=5)
    market_bias: Optional[str] = Field(default=None, max_length=4000)


class TradingDayRead(BaseModel):
    id: int
    date: date_type
    status: str
    sleep_quality: Optional[int]
    mood: Optional[int]
    market_bias: Optional[str]
    has_bias_chart: bool
    checklist: list[ChecklistCompletionRead]
    created_at: datetime
    updated_at: datetime


class TradingDaySummary(BaseModel):
    """Lightweight entry for the calendar list view."""

    date: date_type
    status: str
    has_bias_chart: bool
    checklist_completed_count: int
    checklist_total_count: int
