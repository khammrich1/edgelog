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
import re
from decimal import Decimal
from typing import Optional

# Per-point (per full contract) dollar value.
INSTRUMENT_MULTIPLIERS: dict[str, Decimal] = {
    "MNQ": Decimal("2"),    # Micro E-mini Nasdaq-100
    "MES": Decimal("5"),    # Micro E-mini S&P 500
    "MGC": Decimal("10"),   # Micro Gold (10 troy oz)
    "MCL": Decimal("100"),  # Micro WTI Crude Oil (100 barrels)
    "NQ": Decimal("20"),    # E-mini Nasdaq-100
    "ES": Decimal("50"),    # E-mini S&P 500
    "GC": Decimal("100"),   # Gold (100 troy oz)
}

# Minimum price increment (one tick). Used to sanity-check a price -- manual
# or AI-extracted -- against the contract's real quoting granularity; it is
# not used for P&L math (which only needs the multiplier above).
INSTRUMENT_TICK_SIZES: dict[str, Decimal] = {
    "MNQ": Decimal("0.25"),
    "MES": Decimal("0.25"),
    "MGC": Decimal("0.1"),
    "MCL": Decimal("0.01"),
    "NQ": Decimal("0.25"),
    "ES": Decimal("0.25"),
    "GC": Decimal("0.1"),
}

# Standard futures contract-month codes (CME convention): F=Jan G=Feb H=Mar
# J=Apr K=May M=Jun N=Jul Q=Aug U=Sep V=Oct X=Nov Z=Dec. A dated contract
# symbol like "MNQZ26" is root "MNQ" + month code "Z" + 1-4 digit year; the
# per-point dollar value doesn't depend on expiry, so it should resolve to
# exactly the same multiplier as its root.
_CONTRACT_MONTH_CODES = "FGHJKMNQUVXZ"
_DATED_CONTRACT_RE = re.compile(rf"^([A-Z]{{1,3}})[{_CONTRACT_MONTH_CODES}]\d{{1,4}}$")


def get_multiplier(symbol: str) -> Optional[Decimal]:
    """Returns the known per-point dollar multiplier for a symbol, or None
    if EdgeLog has no verified contract spec for it. Accepts either a bare
    root (MNQ) or a dated contract (MNQZ26) -- see _DATED_CONTRACT_RE."""
    normalized = symbol.strip().upper()
    multiplier = INSTRUMENT_MULTIPLIERS.get(normalized)
    if multiplier is not None:
        return multiplier

    match = _DATED_CONTRACT_RE.match(normalized)
    if match:
        return INSTRUMENT_MULTIPLIERS.get(match.group(1))
    return None


def get_tick_size(symbol: str) -> Optional[Decimal]:
    """Returns the known minimum price increment for a symbol, or None if
    EdgeLog has no verified contract spec for it. Same root/dated-contract
    resolution as get_multiplier."""
    normalized = symbol.strip().upper()
    tick_size = INSTRUMENT_TICK_SIZES.get(normalized)
    if tick_size is not None:
        return tick_size

    match = _DATED_CONTRACT_RE.match(normalized)
    if match:
        return INSTRUMENT_TICK_SIZES.get(match.group(1))
    return None


def tick_alignment_warning(symbol: str, field_label: str, price: Optional[Decimal]) -> Optional[str]:
    """Returns a human-readable warning if `price` is not a whole-number
    multiple of the instrument's tick size (e.g. a misread digit producing
    31224.10 for MNQ, whose ticks only ever land on a .00/.25/.50/.75). None
    if the symbol's tick size is unknown or the price is tick-aligned (or
    not supplied) -- callers should treat "no warning" as "nothing to flag",
    not as "confirmed correct"."""
    if price is None:
        return None
    tick_size = get_tick_size(symbol)
    if tick_size is None:
        return None
    remainder = price % tick_size
    if remainder != Decimal("0"):
        return (
            f"{field_label} {price} is not aligned to {symbol.strip().upper()}'s "
            f"{tick_size} tick size -- double-check this against the source for a misread digit."
        )
    return None
