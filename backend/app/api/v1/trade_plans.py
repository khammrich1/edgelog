"""Pre-trade plan endpoints (issue #59): Plan -> Review -> Approve/Reject.

A TradePlan is reviewed and explicitly approved or rejected by the trader
before any execution exists. Nothing in this module ever creates, updates,
or reads a Trade/TradeEntry/TradeExit row, calls a broker, or originates an
order -- approving a plan records an intent only. See
docs/PRODUCT_VISION_AND_EXECUTION_2026-10-08.md step 5 and issue #54 for the
(separate, not-yet-built) local Practice handoff that would eventually act
on an approved plan.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.instruments import get_multiplier
from app.models.broker_accounts import BrokerAccount
from app.models.trade_plans import TradePlan
from app.models.user import User
from app.schemas.trade_plans import (
    TERMINAL_STATUSES,
    TradePlanCreate,
    TradePlanDecision,
    TradePlanRead,
)

router = APIRouter()

EXPIRED_DECISION_NOTE = "Expired automatically: the plan's validity window (expires_at) passed before a decision was recorded."


async def _get_owned_plan(db: AsyncSession, user_id: int, plan_id: int) -> TradePlan:
    result = await db.execute(
        select(TradePlan).where(TradePlan.id == plan_id, TradePlan.user_id == user_id)
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade plan not found")
    return plan


async def _is_superseded(db: AsyncSession, plan_id: int) -> bool:
    result = await db.execute(select(TradePlan.id).where(TradePlan.previous_version_id == plan_id))
    return result.scalar_one_or_none() is not None


async def _require_owned_broker_account(db: AsyncSession, user_id: int, broker_account_id: Optional[int]) -> None:
    """Reuses the broker-accounts registry (issue #95) rather than a
    free-text account field -- so a plan can never be bound to another
    trader's registered account."""
    if broker_account_id is None:
        return
    result = await db.execute(
        select(BrokerAccount.id).where(BrokerAccount.id == broker_account_id, BrokerAccount.user_id == user_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broker account not found")


async def _resolve_broker_account(db: AsyncSession, broker_account_id: Optional[int]) -> Optional[BrokerAccount]:
    if broker_account_id is None:
        return None
    result = await db.execute(select(BrokerAccount).where(BrokerAccount.id == broker_account_id))
    return result.scalar_one_or_none()


async def _maybe_expire(db: AsyncSession, plan: TradePlan) -> TradePlan:
    """Lazily transitions a stale pending plan to expired, using the
    server's own clock -- never the client's. Idempotent: a plan that is
    already past expires_at but not pending is left alone, since expired
    is only ever reached FROM pending (approved/rejected/invalidated/
    canceled are already terminal and must not be overwritten)."""
    if plan.status == "pending" and plan.expires_at <= datetime.now(timezone.utc):
        plan.status = "expired"
        plan.decided_at = datetime.now(timezone.utc)
        plan.decision_note = EXPIRED_DECISION_NOTE
        await db.flush()
        await db.refresh(plan)
    return plan


def _compute_risk_reward(plan: TradePlan) -> dict:
    sign = Decimal(1) if plan.direction == "long" else Decimal(-1)
    quantity = Decimal(plan.quantity)

    risk_per_unit = (plan.entry_price - plan.stop_price) * sign
    risk_points = risk_per_unit * quantity

    reward_points: Optional[Decimal] = None
    if plan.target_price is not None:
        reward_per_unit = (plan.target_price - plan.entry_price) * sign
        reward_points = reward_per_unit * quantity

    multiplier = get_multiplier(plan.symbol)
    multiplier_known = multiplier is not None
    risk_dollars = risk_points * multiplier if multiplier_known else None
    reward_dollars = (reward_points * multiplier) if (multiplier_known and reward_points is not None) else None

    reward_risk_ratio: Optional[Decimal] = None
    if reward_points is not None and risk_points > 0:
        reward_risk_ratio = reward_points / risk_points

    exceeds_max_risk: Optional[bool] = None
    if risk_dollars is not None and plan.max_risk_dollars is not None:
        exceeds_max_risk = risk_dollars > plan.max_risk_dollars

    return {
        "risk_points": risk_points,
        "risk_dollars": risk_dollars,
        "reward_points": reward_points,
        "reward_dollars": reward_dollars,
        "reward_risk_ratio": reward_risk_ratio,
        "multiplier_known": multiplier_known,
        "exceeds_max_risk": exceeds_max_risk,
    }


async def _serialize_plan(db: AsyncSession, plan: TradePlan) -> TradePlanRead:
    is_latest = not await _is_superseded(db, plan.id)
    math = _compute_risk_reward(plan)
    broker_account = await _resolve_broker_account(db, plan.broker_account_id)
    return TradePlanRead(
        id=plan.id,
        previous_version_id=plan.previous_version_id,
        revision_number=plan.revision_number,
        is_latest_revision=is_latest,
        broker_account_id=plan.broker_account_id,
        broker_account_label=broker_account.label if broker_account else None,
        broker_account_provider=broker_account.provider if broker_account else None,
        broker_account_account_id=broker_account.account_id if broker_account else None,
        symbol=plan.symbol,
        direction=plan.direction,
        entry_price=plan.entry_price,
        stop_price=plan.stop_price,
        target_price=plan.target_price,
        quantity=plan.quantity,
        max_risk_dollars=plan.max_risk_dollars,
        setup=plan.setup,
        invalidation_condition=plan.invalidation_condition,
        rationale=plan.rationale,
        expires_at=plan.expires_at,
        status=plan.status,
        decided_at=plan.decided_at,
        decision_note=plan.decision_note,
        created_at=plan.created_at,
        **math,
    )


def _new_plan_from_payload(user_id: int, payload: TradePlanCreate, *, previous_version_id: Optional[int], revision_number: int) -> TradePlan:
    return TradePlan(
        user_id=user_id,
        previous_version_id=previous_version_id,
        revision_number=revision_number,
        broker_account_id=payload.broker_account_id,
        symbol=payload.symbol,
        direction=payload.direction,
        entry_price=payload.entry_price,
        stop_price=payload.stop_price,
        target_price=payload.target_price,
        quantity=payload.quantity,
        max_risk_dollars=payload.max_risk_dollars,
        setup=payload.setup,
        invalidation_condition=payload.invalidation_condition,
        rationale=payload.rationale,
        expires_at=payload.expires_at,
        status="pending",
    )


# ---- CRUD / review ----

@router.post("/trade-plans", response_model=TradePlanRead, status_code=status.HTTP_201_CREATED)
async def create_trade_plan(
    payload: TradePlanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="expires_at must be in the future")
    await _require_owned_broker_account(db, current_user.id, payload.broker_account_id)

    plan = _new_plan_from_payload(current_user.id, payload, previous_version_id=None, revision_number=1)
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    return await _serialize_plan(db, plan)


@router.get("/trade-plans", response_model=list[TradePlanRead])
async def list_trade_plans(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    include_superseded: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TradePlan).where(TradePlan.user_id == current_user.id).order_by(TradePlan.created_at.desc(), TradePlan.id.desc())
    )
    plans = list(result.scalars().all())
    for plan in plans:
        await _maybe_expire(db, plan)

    serialized = [await _serialize_plan(db, plan) for plan in plans]
    if not include_superseded:
        serialized = [p for p in serialized if p.is_latest_revision]
    if status_filter is not None:
        serialized = [p for p in serialized if p.status == status_filter]
    return serialized


@router.get("/trade-plans/{plan_id}", response_model=TradePlanRead)
async def get_trade_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await _get_owned_plan(db, current_user.id, plan_id)
    plan = await _maybe_expire(db, plan)
    return await _serialize_plan(db, plan)


def _require_pending(plan: TradePlan) -> None:
    if plan.status != "pending":
        if plan.status in TERMINAL_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Plan is already {plan.status} and cannot be changed",
            )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Plan is not pending")


@router.post("/trade-plans/{plan_id}/approve", response_model=TradePlanRead)
async def approve_trade_plan(
    plan_id: int,
    payload: Optional[TradePlanDecision] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await _get_owned_plan(db, current_user.id, plan_id)
    plan = await _maybe_expire(db, plan)
    _require_pending(plan)

    math = _compute_risk_reward(plan)
    if not math["multiplier_known"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot approve: '{plan.symbol}' has no verified instrument multiplier, "
                "so dollar risk cannot be validated. Add a multiplier for this symbol before approving."
            ),
        )

    plan.status = "approved"
    plan.decided_at = datetime.now(timezone.utc)
    plan.decision_note = payload.decision_note if payload else None
    await db.flush()
    await db.refresh(plan)
    return await _serialize_plan(db, plan)


@router.post("/trade-plans/{plan_id}/reject", response_model=TradePlanRead)
async def reject_trade_plan(
    plan_id: int,
    payload: Optional[TradePlanDecision] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await _get_owned_plan(db, current_user.id, plan_id)
    plan = await _maybe_expire(db, plan)
    _require_pending(plan)

    plan.status = "rejected"
    plan.decided_at = datetime.now(timezone.utc)
    plan.decision_note = payload.decision_note if payload else None
    await db.flush()
    await db.refresh(plan)
    return await _serialize_plan(db, plan)


@router.post("/trade-plans/{plan_id}/invalidate", response_model=TradePlanRead)
async def invalidate_trade_plan(
    plan_id: int,
    payload: Optional[TradePlanDecision] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """The setup condition itself broke down (e.g. price structure no
    longer matches) before the trader ever decided to approve or reject --
    a distinct, legitimate never-executed outcome from a deliberate reject."""
    plan = await _get_owned_plan(db, current_user.id, plan_id)
    plan = await _maybe_expire(db, plan)
    _require_pending(plan)

    plan.status = "invalidated"
    plan.decided_at = datetime.now(timezone.utc)
    plan.decision_note = payload.decision_note if payload else None
    await db.flush()
    await db.refresh(plan)
    return await _serialize_plan(db, plan)


@router.post("/trade-plans/{plan_id}/cancel", response_model=TradePlanRead)
async def cancel_trade_plan(
    plan_id: int,
    payload: Optional[TradePlanDecision] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trader withdraws a plan outright (e.g. no longer relevant), distinct
    from reject (declined after review) and invalidate (setup broke down).
    Allowed from pending OR approved -- an approved-but-not-yet-executed
    plan the trader no longer intends to act on is exactly the
    'never executed' outcome this product must preserve, not erase."""
    plan = await _get_owned_plan(db, current_user.id, plan_id)
    plan = await _maybe_expire(db, plan)
    if plan.status not in ("pending", "approved"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Plan is already {plan.status} and cannot be canceled",
        )

    plan.status = "canceled"
    plan.decided_at = datetime.now(timezone.utc)
    plan.decision_note = payload.decision_note if payload else None
    await db.flush()
    await db.refresh(plan)
    return await _serialize_plan(db, plan)


@router.post("/trade-plans/{plan_id}/revise", response_model=TradePlanRead, status_code=status.HTTP_201_CREATED)
async def revise_trade_plan(
    plan_id: int,
    payload: TradePlanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new pending plan that supersedes `plan_id`, instead of
    mutating it -- the prior plan's own status/decided_at/decision_note are
    never touched, so an approved (or rejected/expired/invalidated/
    canceled) plan's record stays exactly as it was decided. Only the
    latest revision in a chain may be revised again."""
    plan = await _get_owned_plan(db, current_user.id, plan_id)
    plan = await _maybe_expire(db, plan)

    if await _is_superseded(db, plan.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A newer revision of this plan already exists; revise that one instead",
        )
    if payload.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="expires_at must be in the future")
    await _require_owned_broker_account(db, current_user.id, payload.broker_account_id)

    new_plan = _new_plan_from_payload(
        current_user.id, payload, previous_version_id=plan.id, revision_number=plan.revision_number + 1
    )
    db.add(new_plan)
    await db.flush()
    await db.refresh(new_plan)
    return await _serialize_plan(db, new_plan)
