"""Annual P&L / Financial Tracker schemas. A flat cash ledger, independent
of Trade/TradingDay -- see app/models/financial_entries.py."""
from datetime import date as date_type, datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

EntryType = Literal["expense", "income"]


class FinancialEntryCreate(BaseModel):
    entry_type: EntryType
    category: str = Field(min_length=1, max_length=200)
    # Zero is valid -- a free reset or comped item is still worth logging to
    # count the event, even though it cost nothing. Only negative is nonsense.
    amount: Decimal = Field(ge=0)
    date: date_type
    firm: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=4000)


class FinancialEntryBulkCreate(BaseModel):
    """Payload for creating several entries in one request, e.g. after
    reviewing AI-extracted rows from a multi-payout screenshot."""

    entries: List[FinancialEntryCreate] = Field(min_length=1, max_length=100)


class FinancialEntryUpdate(BaseModel):
    entry_type: Optional[EntryType] = None
    category: Optional[str] = Field(default=None, min_length=1, max_length=200)
    amount: Optional[Decimal] = Field(default=None, ge=0)
    date: Optional[date_type] = None
    firm: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=4000)


class FinancialEntryRead(BaseModel):
    id: int
    entry_type: EntryType
    category: str
    amount: Decimal
    date: date_type
    firm: Optional[str]
    notes: Optional[str]
    has_screenshot: bool
    created_at: datetime
    updated_at: datetime


class FinancialEntryExtraction(BaseModel):
    """All-Optional: any field might not be legible in the screenshot.
    Never persisted directly -- only prefills the create form."""

    entry_type: Optional[EntryType] = None
    category: Optional[str] = None
    amount: Optional[Decimal] = None
    date: Optional[date_type] = None
    firm: Optional[str] = None
    notes: Optional[str] = None


class FinancialEntryBulkExtractionItem(FinancialEntryExtraction):
    """One row from a bulk (multi-row table) extraction. possible_duplicate
    is set when an existing entry already matches this row's date, amount,
    and category -- the client defaults such a row to unchecked in the
    review table, but the user can still re-check and import it."""

    possible_duplicate: bool = False
