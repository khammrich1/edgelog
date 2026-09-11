"""Daily Journal models (VS2): trading days and the configurable morning checklist."""
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


class TradingDay(Base):
    """A single day's journal entry: the trader's prep, not their trades."""

    __tablename__ = "trading_days"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_trading_day_user_date"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    status = Column(String, nullable=False, default="draft")  # draft | locked
    sleep_quality = Column(Integer, nullable=True)  # 1-5
    mood = Column(Integer, nullable=True)  # 1-5
    market_bias = Column(Text, nullable=True)
    bias_chart_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ChecklistItem(Base):
    """A user-configured morning checklist item."""

    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TradingDayChecklistItem(Base):
    """Whether a given checklist item was completed on a given trading day.

    A row per (day, item), created the first time a day is opened so a later
    change to the checklist config never rewrites history.
    """

    __tablename__ = "trading_day_checklist_items"
    __table_args__ = (
        UniqueConstraint("trading_day_id", "checklist_item_id", name="uq_day_checklist_item"),
    )

    id = Column(Integer, primary_key=True, index=True)
    trading_day_id = Column(
        Integer, ForeignKey("trading_days.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checklist_item_id = Column(
        Integer, ForeignKey("checklist_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    completed = Column(Boolean, nullable=False, default=False)
