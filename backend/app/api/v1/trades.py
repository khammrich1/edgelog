"""Trade lifecycle endpoints (VS3): manually-logged trades and their exits."""
import json
import uuid
from collections import defaultdict
from decimal import Decimal
from datetime import date as date_type, datetime, timedelta, timezone
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

# DF-VS1 (issue #78): a "verified pre-trade" claim is only plausible if
# this trade is being logged close to when it was actually taken -- a
# trade entered days/weeks ago but journaled just now (or one that
# supposedly hasn't happened yet) cannot have had its plan meaningfully
# "verified before execution" at logging time, whatever the trader checks.
# This is a backstop against the most obviously false claims, not a proof
# of timing: within the window, honoring the flag is still trusting the
# trader's own word that the plan predated the trade.
PLAN_VERIFICATION_MAX_AGE = timedelta(hours=24)
PLAN_VERIFICATION_FUTURE_TOLERANCE = timedelta(minutes=15)

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

    # DF-VS1 (issue #78): risk computed entirely from the immutable plan
    # snapshot (planned_entry_price/planned_stop_price/planned_quantity),
    # never the live entry/stop/quantity -- this is the one that stays
    # "what was the plan" even after the trader moves the stop (e.g. to
    # breakeven) or corrects the entry price, either of which
    # planned_risk_points above deliberately keeps reflecting live.
    original_planned_risk_points: Optional[Decimal] = None
    original_planned_risk_dollars: Optional[Decimal] = None
    if (
        trade.planned_entry_price is not None
        and trade.planned_stop_price is not None
        and trade.planned_quantity is not None
    ):
        original_risk_per_unit = (trade.planned_entry_price - trade.planned_stop_price) * sign
        original_planned_risk_points = original_risk_per_unit * trade.planned_quantity
        if multiplier is not None:
            original_planned_risk_dollars = original_planned_risk_points * multiplier

    # DF-VS1.5a (issue #80): commission/fees left blank anywhere are
    # treated as zero cost for this sum, not unknown cost -- a trade with
    # no cost data recorded anywhere nets to its own gross realized_pnl,
    # which is the honest "no cost known yet" value, not a claim that the
    # cost was actually zero. net_pnl stays null exactly when realized_pnl
    # itself is null (multiplier unknown), same null-propagation as every
    # other dollar figure here.
    total_commission = (trade.commission or Decimal("0")) + sum(
        (e.commission or Decimal("0")) for e in entries
    ) + sum((x.commission or Decimal("0")) for x in exits)
    total_fees = (trade.fees or Decimal("0")) + sum(
        (e.fees or Decimal("0")) for e in entries
    ) + sum((x.fees or Decimal("0")) for x in exits)
    net_pnl = (realized_pnl - total_commission - total_fees) if realized_pnl is not None else None

    return {
        "total_quantity": total_quantity,
        "average_entry_price": average_entry_price,
        "remaining_quantity": remaining_qty,
        "status": computed_status,
        "realized_points": realized_points,
        "realized_pnl": realized_pnl,
        "planned_risk_points": planned_risk_points,
        "planned_risk_dollars": planned_risk_dollars,
        "original_planned_risk_points": original_planned_risk_points,
        "original_planned_risk_dollars": original_planned_risk_dollars,
        "multiplier_known": multiplier is not None,
        "total_commission": total_commission,
        "total_fees": total_fees,
        "net_pnl": net_pnl,
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
        original_planned_risk_points=math["original_planned_risk_points"],
        original_planned_risk_dollars=math["original_planned_risk_dollars"],
        multiplier_known=math["multiplier_known"],
        has_screenshot=trade.screenshot_path is not None,
        price_source=trade.price_source,
        extraction_snapshot=(
            json.loads(trade.extraction_snapshot) if trade.extraction_snapshot is not None else None
        ),
        extracted_at=trade.extracted_at,
        price_edited_after_extraction=trade.price_edited_after_extraction,
        planned_entry_price=trade.planned_entry_price,
        planned_stop_price=trade.planned_stop_price,
        planned_target_price=trade.planned_target_price,
        planned_quantity=trade.planned_quantity,
        plan_rationale=trade.plan_rationale,
        plan_verified_at=trade.plan_verified_at,
        rule_adherence=trade.rule_adherence,
        rule_adherence_note=trade.rule_adherence_note,
        reflection_notes=trade.reflection_notes,
        commission=trade.commission,
        fees=trade.fees,
        total_commission=math["total_commission"],
        total_fees=math["total_fees"],
        net_pnl=math["net_pnl"],
        external_trade_id=trade.external_trade_id,
        external_order_id=trade.external_order_id,
        account_id=trade.account_id,
        account_label=trade.account_label,
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

    # DF-VS1 (issue #78): a "verified pre-trade" claim is only honored when
    # entry_time is close enough to this request's own clock to be
    # plausible -- a trade logged well after it happened (or one claiming
    # an entry_time that hasn't occurred yet) cannot have had its plan
    # genuinely verified before execution, no matter what the trader
    # checked. The checkbox can request plan_verified_at; it cannot compel
    # the server to grant it.
    now = datetime.now(timezone.utc)
    entry_time = payload.entry_time
    if entry_time.tzinfo is None:
        entry_time = entry_time.replace(tzinfo=timezone.utc)
    age = now - entry_time
    plan_verification_plausible = (
        -PLAN_VERIFICATION_FUTURE_TOLERANCE <= age <= PLAN_VERIFICATION_MAX_AGE
    )

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
        price_source=payload.price_source,
        extraction_snapshot=(
            json.dumps(payload.extraction_snapshot, default=str)
            if payload.extraction_snapshot is not None
            else None
        ),
        extracted_at=payload.extracted_at,
        # DF-VS1 (issue #78): the plan snapshot is fixed here, at creation,
        # and nowhere else -- update_trade never touches these fields.
        # planned_entry_price/planned_quantity are always auto-derived from
        # entry_price/initial_quantity so they can't be submitted out of
        # sync with (or used to game) the actual trade. plan_verified_at is
        # stamped from this request's own clock, only when the trader
        # affirmed the plan was recorded before execution AND entry_time
        # makes that plausible; a retrospective entry, or one rejected by
        # the plausibility check above, leaves it null regardless of
        # whether planned_* were filled in.
        planned_entry_price=payload.entry_price,
        planned_stop_price=payload.planned_stop_price,
        planned_target_price=payload.planned_target_price,
        planned_quantity=payload.initial_quantity,
        plan_rationale=payload.plan_rationale,
        plan_verified_at=now if (payload.plan_verified and plan_verification_plausible) else None,
        commission=payload.commission,
        fees=payload.fees,
    )
    db.add(trade)
    await db.flush()

    # DF-VS1.5a (issue #80): one-submission completed-trade entry -- the
    # schema validator already guarantees these three arrive together or
    # not at all, and that exit_quantity <= initial_quantity.
    exits: list[TradeExit] = []
    if payload.exit_price is not None:
        exit_row = TradeExit(
            trade_id=trade.id,
            quantity=payload.exit_quantity,
            exit_price=payload.exit_price,
            exit_time=payload.exit_time,
            commission=payload.exit_commission,
            fees=payload.exit_fees,
        )
        db.add(exit_row)
        await db.flush()
        exits.append(exit_row)
        trade.status = "closed" if payload.exit_quantity >= payload.initial_quantity else "open"
        await db.flush()

    await db.refresh(trade)
    return _serialize_trade(trade, exits, [])


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

    # Issue #64: an image_extracted trade keeps its original extraction_snapshot
    # forever (set once at creation, never touched here) as an audit trail --
    # this flag just records that *something* price-bearing changed since then,
    # so the UI can show "edited since extraction" without diffing the snapshot.
    price_bearing_fields_changed = any(
        [
            payload.entry_price is not None and payload.entry_price != trade.entry_price,
            payload.initial_quantity is not None and payload.initial_quantity != trade.initial_quantity,
            payload.stop_price is not None and payload.stop_price != trade.stop_price,
            payload.target_price is not None and payload.target_price != trade.target_price,
        ]
    )
    if trade.price_source == "image_extracted" and price_bearing_fields_changed:
        trade.price_edited_after_extraction = True

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
    if payload.commission is not None:
        trade.commission = payload.commission
    if payload.fees is not None:
        trade.fees = payload.fees
    # Outcome (DF-VS1): editable after the fact. Note what's deliberately
    # absent from TradeUpdate and so can never appear here: planned_*,
    # plan_rationale, plan_verified_at -- the plan snapshot stays fixed.
    if payload.rule_adherence is not None:
        trade.rule_adherence = payload.rule_adherence
    if payload.rule_adherence_note is not None:
        trade.rule_adherence_note = payload.rule_adherence_note
    if payload.reflection_notes is not None:
        trade.reflection_notes = payload.reflection_notes

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
        commission=payload.commission,
        fees=payload.fees,
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
        commission=payload.commission,
        fees=payload.fees,
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
    if payload.commission is not None:
        exit_row.commission = payload.commission
    if payload.fees is not None:
        exit_row.fees = payload.fees

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
