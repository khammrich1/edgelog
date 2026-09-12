"""Trade lifecycle endpoints (VS3): manually-logged trades and their exits."""
from decimal import Decimal
from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.instruments import get_multiplier
from app.models.journal import TradingDay
from app.models.trades import Trade, TradeExit
from app.models.user import User
from app.schemas.trades import TradeCreate, TradeExitCreate, TradeExitRead, TradeExitUpdate, TradeRead, TradeUpdate

router = APIRouter()

LOCKED_DAY_DETAIL = "Day is locked. Unlock it to make changes."


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


def _require_unlocked(trading_day: TradingDay) -> None:
    if trading_day.status == "locked":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=LOCKED_DAY_DETAIL)


def _compute_trade_math(trade: Trade, exits: list[TradeExit]):
    """Single source of truth for remaining quantity, status, and P&L/risk.

    Status is always derived from remaining quantity rather than trusted
    from the stored column, so it can never drift from the actual exits.
    """
    exited_qty = sum(e.quantity for e in exits)
    remaining_qty = trade.initial_quantity - exited_qty
    computed_status = "closed" if remaining_qty <= 0 else "open"

    sign = Decimal(1) if trade.direction == "long" else Decimal(-1)
    multiplier = get_multiplier(trade.symbol)

    realized_points = Decimal("0")
    for exit_row in exits:
        movement = (exit_row.exit_price - trade.entry_price) * sign
        realized_points += movement * exit_row.quantity
    realized_pnl = realized_points * multiplier if multiplier is not None else None

    planned_risk_points: Optional[Decimal] = None
    planned_risk_dollars: Optional[Decimal] = None
    if trade.stop_price is not None:
        risk_per_unit = (trade.entry_price - trade.stop_price) * sign
        planned_risk_points = risk_per_unit * trade.initial_quantity
        if multiplier is not None:
            planned_risk_dollars = planned_risk_points * multiplier

    return {
        "remaining_quantity": remaining_qty,
        "status": computed_status,
        "realized_points": realized_points,
        "realized_pnl": realized_pnl,
        "planned_risk_points": planned_risk_points,
        "planned_risk_dollars": planned_risk_dollars,
        "multiplier_known": multiplier is not None,
    }


def _serialize_trade(trade: Trade, exits: list[TradeExit]) -> TradeRead:
    math = _compute_trade_math(trade, exits)
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
        remaining_quantity=math["remaining_quantity"],
        exits=[TradeExitRead.model_validate(e) for e in exits],
        realized_points=math["realized_points"],
        realized_pnl=math["realized_pnl"],
        planned_risk_points=math["planned_risk_points"],
        planned_risk_dollars=math["planned_risk_dollars"],
        multiplier_known=math["multiplier_known"],
        created_at=trade.created_at,
        updated_at=trade.updated_at,
    )


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
        serialized.append(_serialize_trade(trade, exits))
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
    return _serialize_trade(trade, [])


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
    return _serialize_trade(trade, exits)


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
    exited_qty = sum(e.quantity for e in exits)

    new_quantity = payload.initial_quantity if payload.initial_quantity is not None else trade.initial_quantity
    if new_quantity < exited_qty:
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

    trade.status = "closed" if (trade.initial_quantity - exited_qty) <= 0 else "open"
    await db.flush()
    await db.refresh(trade)
    return _serialize_trade(trade, exits)


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
    exited_qty = sum(e.quantity for e in exits)
    remaining_qty = trade.initial_quantity - exited_qty
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
    new_remaining = trade.initial_quantity - (exited_qty + payload.quantity)
    trade.status = "closed" if new_remaining <= 0 else "open"
    await db.flush()
    await db.refresh(trade)
    return _serialize_trade(trade, exits)


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
    exit_row = next((e for e in exits if e.id == exit_id), None)
    if exit_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exit not found")

    new_quantity = payload.quantity if payload.quantity is not None else exit_row.quantity
    other_exited_qty = sum(e.quantity for e in exits if e.id != exit_id)
    if other_exited_qty + new_quantity > trade.initial_quantity:
        remaining_for_this_exit = trade.initial_quantity - other_exited_qty
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
    trade.status = "closed" if (trade.initial_quantity - new_exited_qty) <= 0 else "open"
    await db.flush()
    await db.refresh(trade)

    refreshed_exits = await _get_exits(db, trade.id)
    return _serialize_trade(trade, refreshed_exits)


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
    exit_row = next((e for e in exits if e.id == exit_id), None)
    if exit_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exit not found")

    await db.delete(exit_row)
    await db.flush()

    remaining_exits = [e for e in exits if e.id != exit_id]
    exited_qty = sum(e.quantity for e in remaining_exits)
    trade.status = "closed" if (trade.initial_quantity - exited_qty) <= 0 else "open"
    await db.flush()
    await db.refresh(trade)
    return _serialize_trade(trade, remaining_exits)
