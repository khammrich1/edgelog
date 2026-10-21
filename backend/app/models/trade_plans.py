"""Pre-trade plan models (issue #59): an independent, immutable planned-trade
record, reviewed and explicitly approved/rejected by the trader BEFORE any
execution exists. Deliberately NOT a Trade -- a TradePlan never creates a
Trade/TradeEntry/TradeExit row and approving one is a recorded intent only,
never an order. See docs/PRODUCT_VISION_AND_EXECUTION_2026-10-08.md step 5
and issue #54 for the (separate, not-yet-built) local Practice handoff.

Immutability model: a TradePlan's content fields (symbol/direction/prices/
quantity/expiry/etc.) are set once at creation and never updated in place.
"Editing" a plan creates a new row (a revision) via previous_version_id/
revision_number, leaving the prior row's own status/decided_at/decision_note
untouched forever -- whether a row has since been revised is a derived fact
(see _is_superseded in the API layer), not a column that gets overwritten.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.core.database import Base

PRICE_PRECISION = 18
PRICE_SCALE = 6
AMOUNT_PRECISION = 14
AMOUNT_SCALE = 2


class TradePlan(Base):
    """An immutable pre-trade plan: a trader's intended entry, reviewed for
    risk/reward, then explicitly approved or rejected. Distinct from Trade
    (an actual logged fill) -- plans do not require a trading day and are
    never converted into a Trade by any route in this slice."""

    __tablename__ = "trade_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Revision chain: previous_version_id is null for an original plan, and
    # set to the plan it replaces when a trader revises one. revision_number
    # starts at 1 and increments per chain. Nothing ever updates these on an
    # existing row after creation.
    previous_version_id = Column(Integer, ForeignKey("trade_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    revision_number = Column(Integer, nullable=False, default=1)

    # Reuses the broker-accounts registry (issue #95) instead of a
    # free-text account field -- SET NULL (not CASCADE) so deleting a
    # registered account never deletes the plans that referenced it; the
    # plan just loses that attribution, same as a superseded revision
    # never loses its own status.
    broker_account_id = Column(Integer, ForeignKey("broker_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)  # long | short
    entry_price = Column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False)  # intended limit entry
    stop_price = Column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False)
    target_price = Column(Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=True)
    quantity = Column(Integer, nullable=False)
    max_risk_dollars = Column(Numeric(AMOUNT_PRECISION, AMOUNT_SCALE), nullable=True)
    setup = Column(String, nullable=True)  # free text, mirrors Trade.setup
    invalidation_condition = Column(Text, nullable=True)
    rationale = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # pending | approved | rejected | expired | invalidated | canceled.
    # Set once by a lifecycle transition and never overwritten afterward --
    # expired/invalidated/rejected/canceled are all terminal, same as approved.
    status = Column(String, nullable=False, default="pending", index=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision_note = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
