"""Broker-account ownership registry (issue #95).

This table exists to answer exactly one question later slices will need:
"which broker accounts does this EdgeLog user actually hold?" -- not to
answer it yet with certainty. Today there is no provider-backed channel
between EdgeLog's backend and TopstepX (the local Trader Agent never
talks to this backend; see agent/README.md), so nothing recorded here can
be verified against the broker. Every row created by the routes in this
slice is therefore stamped `verification_status="unverified"` -- a
trader's own claim, not a certified fact -- and no code path anywhere
sets it to "verified". That is intentional: inventing verification would
be worse than not having it. See issue #95 for the full reasoning and
what a real verification mechanism would need.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.sql import func

from app.core.database import Base

VERIFICATION_STATUSES = ("unverified", "verified")


class BrokerAccount(Base):
    """One user's claim to own a broker account. Unique per
    (user_id, provider, account_id) so a trader can't register the same
    account twice; a separate partial unique index (see migration 012)
    additionally guarantees at most one user can ever hold a *verified*
    claim on a given (provider, account_id) -- a real account can only
    belong to one person, even though nothing here can confirm that yet."""

    __tablename__ = "broker_accounts"
    __table_args__ = (
        Index("uq_broker_account_user_provider_account", "user_id", "provider", "account_id", unique=True),
        # At most one user can hold a VERIFIED claim on a given
        # (provider, account_id); unverified rows are unconstrained
        # across users since nothing can arbitrate an unverified claim.
        Index(
            "uq_broker_account_verified_provider_account",
            "provider",
            "account_id",
            unique=True,
            postgresql_where=text("verification_status = 'verified'"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String, nullable=False)  # e.g. "topstepx" -- free text, mirrors agent/'s provider naming
    account_id = Column(String, nullable=False)  # the broker's own account identifier, opaque to EdgeLog
    label = Column(String, nullable=True)  # trader's own friendly name, e.g. "Practice 50K"
    verification_status = Column(String, nullable=False, default="unverified")  # "unverified" | "verified"
    verified_at = Column(DateTime(timezone=True), nullable=True)  # set only if verification_status becomes "verified"
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
