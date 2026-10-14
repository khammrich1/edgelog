"""Instrument reference data (VS3): exposes the centralized multiplier
table (app.core.instruments) so the frontend's risk/reward preview reads
from the single source of truth instead of hard-coding per-instrument
dollar values in Vue components."""
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.instruments import INSTRUMENT_MULTIPLIERS, INSTRUMENT_TICK_SIZES
from app.models.user import User

router = APIRouter()


@router.get("/instruments/multipliers")
async def get_instrument_multipliers(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    return {symbol: str(value) for symbol, value in INSTRUMENT_MULTIPLIERS.items()}


@router.get("/instruments/tick-sizes")
async def get_instrument_tick_sizes(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    """Issue #61: the frontend needs tick size (not just the multiplier) to
    compute a tick-aligned breakeven exit price for the B/E quick-exit
    action -- same centralized-table pattern as /instruments/multipliers,
    so a symbol with no verified tick size is simply absent here rather
    than defaulting to some invented value."""
    return {symbol: str(value) for symbol, value in INSTRUMENT_TICK_SIZES.items()}
