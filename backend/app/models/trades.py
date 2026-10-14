"""Trade lifecycle models (VS3): manually-logged trades and their exits."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.core.database import Base

PRICE_PRECISION = 18
PRICE_SCALE = 6
AMOUNT_PRECISION = 14
AMOUNT_SCALE = 2


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
    # Provenance (issue #64): where entry/stop/target/quantity originally
    # came from. "image_extracted" trades carry an immutable snapshot of
    # exactly what the AI returned, so later edits can be audited against
    # the original unverified suggestion rather than silently overwriting it.
    price_source = Column(String, nullable=False, default="manual")  # manual | image_extracted
    extraction_snapshot = Column(Text, nullable=True)  # JSON string, set once at creation, never edited
    extracted_at = Column(DateTime(timezone=True), nullable=True)
    price_edited_after_extraction = Column(Boolean, nullable=False, default=False)
    # Plan (DF-VS1, issue #78): the original intended entry/stop/target/
    # quantity and rationale, set once at creation and never touched by
    # update_trade -- mirrors extraction_snapshot's immutability. Freezing
    # planned_entry_price here too (not just stop/target) means a later
    # correction to the live entry_price can never silently drift the
    # original risk-at-entry math. plan_verified_at is stamped from the
    # server's own clock, never trader-supplied, and only honored when the
    # claim is plausible (see create_trade's entry-time window check);
    # null means the trade was journaled retrospectively, or the "verified
    # pre-trade" claim was rejected as implausible.
    planned_entry_price = Column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=True)
    planned_stop_price = Column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=True)
    planned_target_price = Column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=True)
    planned_quantity = Column(Integer, nullable=True)
    plan_rationale = Column(Text, nullable=True)
    plan_verified_at = Column(DateTime(timezone=True), nullable=True)
    # Outcome (DF-VS1): judged after the fact, editable like notes.
    rule_adherence = Column(String, nullable=True)  # yes | no | unknown
    rule_adherence_note = Column(Text, nullable=True)
    reflection_notes = Column(Text, nullable=True)
    # Commission/fees for the original entry fill (DF-VS1.5a, issue #80).
    # TradeEntry/TradeExit carry their own -- this is Trade's own because
    # the original entry lives on this row, not a synthetic TradeEntry.
    # Left null (not defaulted to 0) when not recorded -- see
    # _compute_trade_math's net_pnl comment for what that means for net P&L.
    commission = Column(Numeric(AMOUNT_PRECISION, AMOUNT_SCALE), nullable=True)
    fees = Column(Numeric(AMOUNT_PRECISION, AMOUNT_SCALE), nullable=True)
    # External/account identifiers (DF-VS1.5b/c groundwork, issue #80).
    # Unused by any route yet -- exist so later import/sync slices don't
    # need a second migration. Provider-agnostic string IDs, not FKs.
    external_trade_id = Column(String, nullable=True)
    external_order_id = Column(String, nullable=True)
    account_id = Column(String, nullable=True)
    account_label = Column(String, nullable=True)
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
    commission = Column(Numeric(AMOUNT_PRECISION, AMOUNT_SCALE), nullable=True)
    fees = Column(Numeric(AMOUNT_PRECISION, AMOUNT_SCALE), nullable=True)
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
    commission = Column(Numeric(AMOUNT_PRECISION, AMOUNT_SCALE), nullable=True)
    fees = Column(Numeric(AMOUNT_PRECISION, AMOUNT_SCALE), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
