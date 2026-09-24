"""Annual P&L / Financial Tracker: a flat cash ledger of prop-firm/trading
business expenses and income (payouts), deliberately independent of
Trade/TradingDay -- a payout is a profit-split fraction of a trade's
realized P&L, not the same number, so this must never be summed with or
reconciled against Trade data."""
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.core.database import Base

AMOUNT_PRECISION = 14
AMOUNT_SCALE = 2


class FinancialEntry(Base):
    """A single ledger line. amount is always stored as a positive
    magnitude; entry_type ("expense" | "income") determines its sign when
    computing cost/income/net totals."""

    __tablename__ = "financial_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_type = Column(String, nullable=False)  # expense | income
    category = Column(String, nullable=False)  # free text, e.g. "evaluation fee", "payout"
    amount = Column(Numeric(AMOUNT_PRECISION, AMOUNT_SCALE), nullable=False)
    date = Column(Date, nullable=False, index=True)
    firm = Column(String, nullable=True)  # free-text firm/account, optional
    notes = Column(Text, nullable=True)
    screenshot_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
