"""Trade lifecycle models (VS3): manually-logged trades and their exits."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.core.database import Base

PRICE_PRECISION = 18
PRICE_SCALE = 6


class Trade(Base):
    """A manually-logged trade, entered on a single Trading Day."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    trading_day_id = Column(
        Integer, ForeignKey("trading_days.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)  # long | short
    entry_price = Column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False)
    initial_quantity = Column(Integer, nullable=False)
    entry_time = Column(DateTime(timezone=True), nullable=False)
    stop_price = Column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=True)
    target_price = Column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=True)
    setup = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="open")  # open | closed | canceled
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    screenshot_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class TradeSetup(Base):
    """A user-configured setup/strategy label, offered as a dropdown option
    when logging a trade. Trade.setup itself stays a free-text string --
    this table only supplies the quick-pick options, the same relationship
    SYMBOL_PRESETS has to Trade.symbol on the frontend."""

    __tablename__ = "trade_setups"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TradeExit(Base):
    """A single exit (trim or final) against a Trade."""

    __tablename__ = "trade_exits"

    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    exit_price = Column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False)
    exit_time = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TradeEntry(Base):
    """An additional entry leg (scale-in) against a Trade, beyond its
    original entry_price/initial_quantity. Mirrors TradeExit; the original
    entry stays on the Trade row itself rather than becoming a synthetic
    first row here, so a trade with no scale-ins needs no entries at all."""

    __tablename__ = "trade_entries"

    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False)
    entry_time = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
