"""Instrument metadata for trade P&L/risk calculations (VS3).

This is the single authoritative place a per-point dollar multiplier is
defined. Nothing else in the codebase (backend or frontend) should hard-code
a multiplier -- if a new instrument needs one, add it here.

This is deliberately NOT a market-data/instrument database: it's a small,
hand-verified table of contract specs for the futures EdgeLog users
actually log. An unknown symbol is a perfectly valid trade -- it just can't
safely produce a dollar P&L or dollar risk, since we have no verified point
value for it, so callers should preserve the trade and its price movement
and simply omit the dollar figures rather than guess.
"""
from decimal import Decimal
from typing import Optional

# Per-point (per full contract) dollar value.
INSTRUMENT_MULTIPLIERS: dict[str, Decimal] = {
    "MNQ": Decimal("2"),    # Micro E-mini Nasdaq-100
    "MES": Decimal("5"),    # Micro E-mini S&P 500
    "MGC": Decimal("10"),   # Micro Gold (10 troy oz)
    "NQ": Decimal("20"),    # E-mini Nasdaq-100
    "ES": Decimal("50"),    # E-mini S&P 500
    "GC": Decimal("100"),   # Gold (100 troy oz)
}


def get_multiplier(symbol: str) -> Optional[Decimal]:
    """Returns the known per-point dollar multiplier for a symbol, or None
    if EdgeLog has no verified contract spec for it."""
    return INSTRUMENT_MULTIPLIERS.get(symbol.strip().upper())
