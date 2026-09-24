"""Trade lifecycle endpoints (VS3): manually-logged trades and their exits."""
import uuid
from collections import defaultdict
from decimal import Decimal
from datetime import date as date_type, datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.instruments import get_multiplier
from app.models.journal import TradingDay
from app.models.trades import Trade, TradeEntry, TradeExit, TradeSetup
from app.models.user import User
from app.schemas.trades import (
    TradeCalendarDay,
    TradeCreate,
    TradeEntryCreate,
    TradeEntryRead,
    TradeExitCreate,
    TradeExitRead,
    TradeExitUpdate,
    TradeRead,
    TradeSetupCreate,
    TradeSetupRead,
    TradeSetupUpdate,
    TradeUpdate,
)

router = APIRouter()

LOCKED_DAY_DETAIL = "Day is locked. Unlock it to make changes."

TRADE_SCREENSHOT_DIR = Path(__file__).resolve().parents[3] / "uploads" / "trade_screenshots"
ALLOWED_IMAGE_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


# ---- Shared lookups ----

async def _get_owned_trading_day(db: AsyncSession, user_id: int, day: date_type) -> TradingDay:
    result = await db.execute(
        select(TradingDay).where(TradingDay.user_id == user_id, TradingDay.date == day)
    )
    trading_day = result.scalar_one_or_none()
    if trading_day is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No journal entry for this day yet")
    return trading_day


async def _get_owned_trade(db: AsyncSession, user_id: int, trading_day_id: int, trade_id: int) -> Trade:
    result = await db.execute(
        select(Trade).where(
            Trade.id == trade_id, Trade.user_id == user_id, Trade.trading_day_id == trading_day_id
        )
    )
    trade = result.scalar_one_or_none()
    if trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")
    return trade


async def _get_exits(db: AsyncSession, trade_id: int) -> list[TradeExit]:
    result = await db.execute(
        select(TradeExit).where(TradeExit.trade_id == trade_id).order_by(TradeExit.exit_time, TradeExit.id)
    )
    return list(result.scalars().all())


async def _get_entries(db: AsyncSession, trade_id: int) -> list[TradeEntry]:
    result = await db.execute(
        select(TradeEntry).where(TradeEntry.trade_id == trade_id).order_by(TradeEntry.entry_time, TradeEntry.id)
    )
    return list(result.scalars().all())


def _require_unlocked(trading_day: TradingDay) -> None:
    if trading_day.status == "locked":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=LOCKED_DAY_DETAIL)


def _compute_trade_math(trade: Trade, exits: list[TradeExit], entries: list[TradeEntry]):
    """Single source of truth for total/remaining quantity, average entry
    price, status, and P&L/risk.

    Status is always derived from remaining quantity (and canceled_at)
    rather than trusted from the stored column, so it can never drift from
    the actual exits. Average entry price is a quantity-weighted average of
    the original entry plus any scale-in entries; it equals trade.entry_price
    exactly when there are no scale-ins.
    """
    total_quantity = trade.initial_quantity + sum(e.quantity for e in entries)
    total_entry_value = trade.entry_price * trade.initial_quantity + sum(
        e.entry_price * e.quantity for e in entries
    )
    average_entry_price = total_entry_value / total_quantity

    exited_qty = sum(e.quantity for e in exits)
    remaining_qty = total_quantity - exited_qty

    if trade.canceled_at is not None:
        computed_status = "canceled"
    else:
        computed_status = "closed" if remaining_qty <= 0 else "open"

    sign = Decimal(1) if trade.direction == "long" else Decimal(-1)
    multiplier = get_multiplier(trade.symbol)

    realized_points = Decimal("0")
    for exit_row in exits:
        movement = (exit_row.exit_price - average_entry_price) * sign
        realized_points += movement * exit_row.quantity
    realized_pnl = realized_points * multiplier if multiplier is not None else None

    planned_risk_points: Optional[Decimal] = None
    planned_risk_dollars: Optional[Decimal] = None
    if trade.stop_price is not None:
        risk_per_unit = (average_entry_price - trade.stop_price) * sign
        planned_risk_points = risk_per_unit * total_quantity
        if multiplier is not None:
            planned_risk_dollars = planned_risk_points * multiplier

    return {
        "total_quantity": total_quantity,
        "average_entry_price": average_entry_price,
        "remaining_quantity": remaining_qty,
        "status": computed_status,
        "realized_points": realized_points,
        "realized_pnl": realized_pnl,
        "planned_risk_points": planned_risk_points,
        "planned_risk_dollars": planned_risk_dollars,
        "multiplier_known": multiplier is not None,
    }


def _serialize_trade(trade: Trade, exits: list[TradeExit], entries: list[TradeEntry]) -> TradeRead:
    math = _compute_trade_math(trade, exits, entries)
    return TradeRead(
        id=trade.id,
        trading_day_id=trade.trading_day_id,
        symbol=trade.symbol,
        direction=trade.direction,
        entry_price=trade.entry_price,
        initial_quantity=trade.initial_quantity,
        entry_time=trade.entry_time,
        stop_price=trade.stop_price,
        target_price=trade.target_price,
        setup=trade.setup,
        notes=trade.notes,
        status=math["status"],
        canceled_at=trade.canceled_at,
        remaining_quantity=math["remaining_quantity"],
        total_quantity=math["total_quantity"],
        average_entry_price=math["average_entry_price"],
        entries=[TradeEntryRead.model_validate(e) for e in entries],
        exits=[TradeExitRead.model_validate(e) for e in exits],
        realized_points=math["realized_points"],
        realized_pnl=math["realized_pnl"],
        planned_risk_points=math["planned_risk_points"],
        planned_risk_dollars=math["planned_risk_dollars"],
        multiplier_known=math["multiplier_known"],
        has_screenshot=trade.screenshot_path is not None,
        created_at=trade.created_at,
        updated_at=trade.updated_at,
    )


# ---- Trade setup configuration ----

@router.get("/trade-setups", response_model=list[TradeSetupRead])
async def list_trade_setups(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(TradeSetup).where(TradeSetup.user_id == current_user.id)
    if not include_inactive:
        query = query.where(TradeSetup.is_active.is_(True))
    query = query.order_by(TradeSetup.sort_order, TradeSetup.id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/trade-setups", response_model=TradeSetupRead, status_code=status.HTTP_201_CREATED)
async def create_trade_setup(
    payload: TradeSetupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    max_order_result = await db.execute(
        select(func.max(TradeSetup.sort_order)).where(TradeSetup.user_id == current_user.id)
    )
    next_order = (max_order_result.scalar() or 0) + 1

    setup = TradeSetup(user_id=current_user.id, name=payload.name, sort_order=next_order)
    db.add(setup)
    await db.flush()
    await db.refresh(setup)
    return setup


@router.put("/trade-setups/{setup_id}", response_model=TradeSetupRead)
async def update_trade_setup(
    setup_id: int,
    payload: TradeSetupUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    setup = await _get_owned_trade_setup(db, current_user.id, setup_id)

    if payload.name is not None:
        setup.name = payload.name
    if payload.sort_order is not None:
        setup.sort_order = payload.sort_order
    if payload.is_active is not None:
        setup.is_active = payload.is_active

    await db.flush()
    await db.refresh(setup)
    return setup


@router.delete("/trade-setups/{setup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trade_setup(
    setup_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    setup = await _get_owned_trade_setup(db, current_user.id, setup_id)
    # Soft delete: a trade already logged with this setup keeps its own
    # setup string regardless of later changes to the configured list.
    setup.is_active = False
    await db.flush()


async def _get_owned_trade_setup(db: AsyncSession, user_id: int, setup_id: int) -> TradeSetup:
    result = await db.execute(
        select(TradeSetup).where(TradeSetup.id == setup_id, TradeSetup.user_id == user_id)
    )
    setup = result.scalar_one_or_none()
    if setup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade setup not found")
    return setup


# ---- Trades ----

@router.get("/days/{day}/trades", response_model=list[TradeRead])
async def list_trades(
    day: date_type,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_owned_trading_day(db, current_user.id, day)
    result = await db.execute(
        select(Trade)
        .where(Trade.trading_day_id == trading_day.id)
        .order_by(Trade.entry_time, Trade.id)
    )
    trades = result.scalars().all()

    serialized = []
    for trade in trades:
        exits = await _get_exits(db, trade.id)
        entries = await _get_entries(db, trade.id)
        serialized.append(_serialize_trade(trade, exits, entries))
    return serialized


@router.post("/days/{day}/trades", response_model=TradeRead, status_code=status.HTTP_201_CREATED)
async def create_trade(
    day: date_type,
    payload: TradeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_owned_trading_day(db, current_user.id, day)
    _require_unlocked(trading_day)

    trade = Trade(
        user_id=current_user.id,
        trading_day_id=trading_day.id,
        symbol=payload.symbol.strip().upper(),
        direction=payload.direction,
        entry_price=payload.entry_price,
        initial_quantity=payload.initial_quantity,
        entry_time=payload.entry_time,
        stop_price=payload.stop_price,
        target_price=payload.target_price,
        setup=payload.setup,
        notes=payload.notes,
        status="open",
    )
    db.add(trade)
    await db.flush()
    await db.refresh(trade)
    return _serialize_trade(trade, [], [])


@router.get("/days/{day}/trades/{trade_id}", response_model=TradeRead)
async def get_trade(
    day: date_type,
    trade_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_owned_trading_day(db, current_user.id, day)
    trade = await _get_owned_trade(db, current_user.id, trading_day.id, trade_id)
    exits = await _get_exits(db, trade.id)
    entries = await _get_entries(db, trade.id)
    return _serialize_trade(trade, exits, entries)


@router.put("/days/{day}/trades/{trade_id}", response_model=TradeRead)
async def update_trade(
    day: date_type,
    trade_id: int,
    payload: TradeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_owned_trading_day(db, current_user.id, day)
    trade = await _get_owned_trade(db, current_user.id, trading_day.id, trade_id)
    _require_unlocked(trading_day)

    exits = await _get_exits(db, trade.id)
    entries = await _get_entries(db, trade.id)
    exited_qty = sum(e.quantity for e in exits)
    entries_qty = sum(e.quantity for e in entries)

    new_initial_quantity = (
        payload.initial_quantity if payload.initial_quantity is not None else trade.initial_quantity
    )
    if new_initial_quantity + entries_qty < exited_qty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot set quantity below the {exited_qty} contracts/shares already exited",
        )

    if payload.symbol is not None:
        trade.symbol = payload.symbol.strip().upper()
    if payload.direction is not None:
        trade.direction = payload.direction
    if payload.entry_price is not None:
        trade.entry_price = payload.entry_price
    if payload.initial_quantity is not None:
        trade.initial_quantity = payload.initial_quantity
    if payload.entry_time is not None:
        trade.entry_time = payload.entry_time
    if payload.stop_price is not None:
        trade.stop_price = payload.stop_price
    if payload.target_price is not None:
        trade.target_price = payload.target_price
    if payload.setup is not None:
        trade.setup = payload.setup
    if payload.notes is not None:
        trade.notes = payload.notes

    await db.flush()
    math = _compute_trade_math(trade, exits, entries)
    trade.status = math["status"]
    await db.flush()
    await db.refresh(trade)
    return _serialize_trade(trade, exits, entries)


@router.delete("/days/{day}/trades/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trade(
    day: date_type,
    trade_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_owned_trading_day(db, current_user.id, day)
    trade = await _get_owned_trade(db, current_user.id, trading_day.id, trade_id)
    _require_unlocked(trading_day)

    await db.delete(trade)
    await db.flush()


@router.post("/days/{day}/trades/{trade_id}/cancel", response_model=TradeRead)
async def cancel_trade(
    day: date_type,
    trade_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Marks a trade Canceled instead of deleting it -- for a trade that was
    logged but never really happened (e.g. invalidated before anything was
    realized against it). Only allowed while nothing has been recorded
    beyond the original entry, since a trade with real exits or scale-ins
    represents money that actually moved."""
    trading_day = await _get_owned_trading_day(db, current_user.id, day)
    trade = await _get_owned_trade(db, current_user.id, trading_day.id, trade_id)
    _require_unlocked(trading_day)

    if trade.canceled_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trade is already canceled")

    exits = await _get_exits(db, trade.id)
    entries = await _get_entries(db, trade.id)
    if exits or entries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a trade that already has exits or additional entries recorded",
        )

    trade.canceled_at = datetime.now(timezone.utc)
    trade.status = "canceled"
    await db.flush()
    await db.refresh(trade)
    return _serialize_trade(trade, exits, entries)


# ---- Entries (scale-ins) ----

@router.post(
    "/days/{day}/trades/{trade_id}/entries", response_model=TradeRead, status_code=status.HTTP_201_CREATED
)
async def create_entry(
    day: date_type,
    trade_id: int,
    payload: TradeEntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_owned_trading_day(db, current_user.id, day)
    trade = await _get_owned_trade(db, current_user.id, trading_day.id, trade_id)
    _require_unlocked(trading_day)

    exits = await _get_exits(db, trade.id)
    entries = await _get_entries(db, trade.id)
    current_status = _compute_trade_math(trade, exits, entries)["status"]
    if current_status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add contracts to a trade that isn't open",
        )

    entry_row = TradeEntry(
        trade_id=trade.id,
        quantity=payload.quantity,
        entry_price=payload.entry_price,
        entry_time=payload.entry_time,
    )
    db.add(entry_row)
    await db.flush()

    entries.append(entry_row)
    await db.refresh(trade)
    return _serialize_trade(trade, exits, entries)


@router.delete("/days/{day}/trades/{trade_id}/entries/{entry_id}", response_model=TradeRead)
async def delete_entry(
    day: date_type,
    trade_id: int,
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_owned_trading_day(db, current_user.id, day)
    trade = await _get_owned_trade(db, current_user.id, trading_day.id, trade_id)
    _require_unlocked(trading_day)

    entries = await _get_entries(db, trade.id)
    entry_row = next((e for e in entries if e.id == entry_id), None)
    if entry_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    exits = await _get_exits(db, trade.id)
    remaining_entries = [e for e in entries if e.id != entry_id]
    exited_qty = sum(e.quantity for e in exits)
    remaining_total_qty = trade.initial_quantity + sum(e.quantity for e in remaining_entries)
    if remaining_total_qty < exited_qty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot remove that entry; {exited_qty} contracts/shares are already exited",
        )

    await db.delete(entry_row)
    await db.flush()
    await db.refresh(trade)
    return _serialize_trade(trade, exits, remaining_entries)


# ---- Exits ----

@router.post("/days/{day}/trades/{trade_id}/exits", response_model=TradeRead, status_code=status.HTTP_201_CREATED)
async def create_exit(
    day: date_type,
    trade_id: int,
    payload: TradeExitCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_owned_trading_day(db, current_user.id, day)
    trade = await _get_owned_trade(db, current_user.id, trading_day.id, trade_id)
    _require_unlocked(trading_day)

    exits = await _get_exits(db, trade.id)
    entries = await _get_entries(db, trade.id)
    total_quantity = trade.initial_quantity + sum(e.quantity for e in entries)
    exited_qty = sum(e.quantity for e in exits)
    remaining_qty = total_quantity - exited_qty
    if payload.quantity > remaining_qty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot exit {payload.quantity}; only {remaining_qty} remain open",
        )

    exit_row = TradeExit(
        trade_id=trade.id,
        quantity=payload.quantity,
        exit_price=payload.exit_price,
        exit_time=payload.exit_time,
    )
    db.add(exit_row)
    await db.flush()

    exits.append(exit_row)
    new_remaining = total_quantity - (exited_qty + payload.quantity)
    trade.status = "closed" if new_remaining <= 0 else "open"
    await db.flush()
    await db.refresh(trade)
    return _serialize_trade(trade, exits, entries)


@router.put("/days/{day}/trades/{trade_id}/exits/{exit_id}", response_model=TradeRead)
async def update_exit(
    day: date_type,
    trade_id: int,
    exit_id: int,
    payload: TradeExitUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_owned_trading_day(db, current_user.id, day)
    trade = await _get_owned_trade(db, current_user.id, trading_day.id, trade_id)
    _require_unlocked(trading_day)

    exits = await _get_exits(db, trade.id)
    entries = await _get_entries(db, trade.id)
    total_quantity = trade.initial_quantity + sum(e.quantity for e in entries)
    exit_row = next((e for e in exits if e.id == exit_id), None)
    if exit_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exit not found")

    new_quantity = payload.quantity if payload.quantity is not None else exit_row.quantity
    other_exited_qty = sum(e.quantity for e in exits if e.id != exit_id)
    if other_exited_qty + new_quantity > total_quantity:
        remaining_for_this_exit = total_quantity - other_exited_qty
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot exit {new_quantity}; only {remaining_for_this_exit} remain open for this exit",
        )

    if payload.quantity is not None:
        exit_row.quantity = payload.quantity
    if payload.exit_price is not None:
        exit_row.exit_price = payload.exit_price
    if payload.exit_time is not None:
        exit_row.exit_time = payload.exit_time

    await db.flush()

    new_exited_qty = other_exited_qty + new_quantity
    trade.status = "closed" if (total_quantity - new_exited_qty) <= 0 else "open"
    await db.flush()
    await db.refresh(trade)

    refreshed_exits = await _get_exits(db, trade.id)
    return _serialize_trade(trade, refreshed_exits, entries)


@router.delete("/days/{day}/trades/{trade_id}/exits/{exit_id}", response_model=TradeRead)
async def delete_exit(
    day: date_type,
    trade_id: int,
    exit_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_owned_trading_day(db, current_user.id, day)
    trade = await _get_owned_trade(db, current_user.id, trading_day.id, trade_id)
    _require_unlocked(trading_day)

    exits = await _get_exits(db, trade.id)
    entries = await _get_entries(db, trade.id)
    total_quantity = trade.initial_quantity + sum(e.quantity for e in entries)
    exit_row = next((e for e in exits if e.id == exit_id), None)
    if exit_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exit not found")

    await db.delete(exit_row)
    await db.flush()

    remaining_exits = [e for e in exits if e.id != exit_id]
    exited_qty = sum(e.quantity for e in remaining_exits)
    trade.status = "closed" if (total_quantity - exited_qty) <= 0 else "open"
    await db.flush()
    await db.refresh(trade)
    return _serialize_trade(trade, remaining_exits, entries)


# ---- Trade screenshot ----

def _remove_existing_trade_screenshot(trade: Trade) -> None:
    if trade.screenshot_path:
        existing = TRADE_SCREENSHOT_DIR / trade.screenshot_path
        if existing.exists():
            existing.unlink()
        trade.screenshot_path = None


@router.post("/days/{day}/trades/{trade_id}/screenshot", response_model=TradeRead)
async def upload_trade_screenshot(
    day: date_type,
    trade_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_owned_trading_day(db, current_user.id, day)
    trade = await _get_owned_trade(db, current_user.id, trading_day.id, trade_id)
    _require_unlocked(trading_day)

    extension = ALLOWED_IMAGE_TYPES.get(file.content_type)
    if extension is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image is too large (max 5MB)")

    TRADE_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    _remove_existing_trade_screenshot(trade)

    filename = f"{uuid.uuid4().hex}.{extension}"
    (TRADE_SCREENSHOT_DIR / filename).write_bytes(contents)

    trade.screenshot_path = filename
    await db.flush()
    await db.refresh(trade)

    exits = await _get_exits(db, trade.id)
    entries = await _get_entries(db, trade.id)
    return _serialize_trade(trade, exits, entries)


@router.get("/days/{day}/trades/{trade_id}/screenshot")
async def get_trade_screenshot(
    day: date_type,
    trade_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_owned_trading_day(db, current_user.id, day)
    trade = await _get_owned_trade(db, current_user.id, trading_day.id, trade_id)

    if trade.screenshot_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No screenshot for this trade")

    file_path = TRADE_SCREENSHOT_DIR / trade.screenshot_path
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screenshot file missing")

    return FileResponse(file_path)


@router.delete("/days/{day}/trades/{trade_id}/screenshot", response_model=TradeRead)
async def delete_trade_screenshot(
    day: date_type,
    trade_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_owned_trading_day(db, current_user.id, day)
    trade = await _get_owned_trade(db, current_user.id, trading_day.id, trade_id)
    _require_unlocked(trading_day)

    _remove_existing_trade_screenshot(trade)
    await db.flush()
    await db.refresh(trade)

    exits = await _get_exits(db, trade.id)
    entries = await _get_entries(db, trade.id)
    return _serialize_trade(trade, exits, entries)


# ---- Trade Calendar range query (VS4) ----

async def _get_trades_in_range(
    db: AsyncSession, user_id: int, start: date_type, end: date_type
) -> list[TradeCalendarDay]:
    """Single JOIN plus two batched exit/entry queries, regardless of how
    many trades fall in the range -- avoids the N+1 amplification the
    per-day endpoint's per-trade loop would cause across a full week."""
    result = await db.execute(
        select(Trade, TradingDay.date)
        .join(TradingDay, Trade.trading_day_id == TradingDay.id)
        .where(
            TradingDay.user_id == user_id,
            TradingDay.date >= start,
            TradingDay.date <= end,
        )
        .order_by(TradingDay.date, Trade.entry_time, Trade.id)
    )
    rows = result.all()
    trade_ids = [trade.id for trade, _ in rows]

    exits_by_trade: dict[int, list[TradeExit]] = defaultdict(list)
    entries_by_trade: dict[int, list[TradeEntry]] = defaultdict(list)
    if trade_ids:
        exits_result = await db.execute(
            select(TradeExit)
            .where(TradeExit.trade_id.in_(trade_ids))
            .order_by(TradeExit.exit_time, TradeExit.id)
        )
        for exit_row in exits_result.scalars().all():
            exits_by_trade[exit_row.trade_id].append(exit_row)

        entries_result = await db.execute(
            select(TradeEntry)
            .where(TradeEntry.trade_id.in_(trade_ids))
            .order_by(TradeEntry.entry_time, TradeEntry.id)
        )
        for entry_row in entries_result.scalars().all():
            entries_by_trade[entry_row.trade_id].append(entry_row)

    days: dict[date_type, list[TradeRead]] = {}
    for trade, day_date in rows:
        serialized = _serialize_trade(trade, exits_by_trade[trade.id], entries_by_trade[trade.id])
        days.setdefault(day_date, []).append(serialized)

    return [TradeCalendarDay(date=day_date, trades=day_trades) for day_date, day_trades in days.items()]


@router.get("/trades", response_model=list[TradeCalendarDay])
async def list_trades_in_range(
    start: date_type,
    end: date_type,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trades across a date range, grouped by the day they occurred --
    backs the Trade Calendar (VS4). Unlike the single-day endpoint, this is
    a pure read: it never creates a TradingDay row for a date that was
    never opened, so browsing the calendar has no side effects."""
    if end < start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end must not be before start")

    return await _get_trades_in_range(db, current_user.id, start, end)
