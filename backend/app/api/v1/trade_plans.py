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
from typing import Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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
SUPERSEDED_DETAIL = "A newer revision of this plan exists; decide that one instead"


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


async def _get_owned_broker_account(
    db: AsyncSession, user_id: int, broker_account_id: Optional[int]
) -> Optional[BrokerAccount]:
    """Validates ownership AND returns the row, so callers can snapshot its
    provider/account_id/label onto the new plan -- see _new_plan_from_payload.
    Returns None only when broker_account_id itself is None; an id that
    doesn't belong to this user is a 404, never silently ignored."""
    if broker_account_id is None:
        return None
    result = await db.execute(
        select(BrokerAccount).where(BrokerAccount.id == broker_account_id, BrokerAccount.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broker account not found")
    return account


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


def _serialize_plan(plan: TradePlan, *, is_latest: bool, math: Optional[dict] = None) -> TradePlanRead:
    """Synchronous and DB-free: broker account identity comes from the
    snapshot columns on `plan` itself (never a live join -- see the model
    docstring), and is_latest/math are supplied by the caller, which
    already has whatever it needs to compute them without a second query
    or a second risk/reward pass over the same plan."""
    if math is None:
        math = _compute_risk_reward(plan)
    return TradePlanRead(
        id=plan.id,
        previous_version_id=plan.previous_version_id,
        revision_number=plan.revision_number,
        is_latest_revision=is_latest,
        broker_account_id=plan.broker_account_id,
        broker_account_label=plan.broker_account_label,
        broker_account_provider=plan.broker_account_provider,
        broker_account_account_id=plan.broker_account_account_id,
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


async def _serialize_plan_live(db: AsyncSession, plan: TradePlan) -> TradePlanRead:
    """Single-plan path (get/approve/reject/.../revise): no larger result
    set is already in memory, so is_latest is resolved with one live query."""
    is_latest = not await _is_superseded(db, plan.id)
    return _serialize_plan(plan, is_latest=is_latest)


def _new_plan_from_payload(
    user_id: int,
    payload: TradePlanCreate,
    *,
    previous_version_id: Optional[int],
    revision_number: int,
    broker_account: Optional[BrokerAccount],
) -> TradePlan:
    return TradePlan(
        user_id=user_id,
        previous_version_id=previous_version_id,
        revision_number=revision_number,
        broker_account_id=payload.broker_account_id,
        broker_account_provider=broker_account.provider if broker_account else None,
        broker_account_account_id=broker_account.account_id if broker_account else None,
        broker_account_label=broker_account.label if broker_account else None,
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
    broker_account = await _get_owned_broker_account(db, current_user.id, payload.broker_account_id)

    plan = _new_plan_from_payload(
        current_user.id, payload, previous_version_id=None, revision_number=1, broker_account=broker_account
    )
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    return await _serialize_plan_live(db, plan)


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

    # The user's full plan set is already loaded above, so "is this plan
    # superseded" is answered from that in-memory set instead of firing one
    # extra SELECT per plan (an N+1 query pattern caught in review) -- any
    # plan whose id appears as another plan's previous_version_id has been
    # superseded.
    superseded_ids = {p.previous_version_id for p in plans if p.previous_version_id is not None}

    serialized = [_serialize_plan(plan, is_latest=plan.id not in superseded_ids) for plan in plans]
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
    return await _serialize_plan_live(db, plan)


def _check_source_status(plan: TradePlan, allowed_statuses: tuple[str, ...]) -> None:
    if plan.status not in allowed_statuses:
        if plan.status in TERMINAL_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Plan is already {plan.status} and cannot be changed",
            )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Plan is not pending")


async def _decide_plan(
    db: AsyncSession,
    user_id: int,
    plan_id: int,
    new_status: str,
    decision_note: Optional[str],
    *,
    allowed_statuses: tuple[str, ...] = ("pending",),
    extra_check: Optional[Callable[[TradePlan], None]] = None,
) -> TradePlan:
    """Shared body for approve/reject/invalidate/cancel: fetch, lazily
    expire, refuse a superseded or already-decided plan, run any
    endpoint-specific gate (e.g. approve's multiplier/risk-ceiling check),
    then transition. Centralizing this means the "can't act on a
    superseded or already-decided plan" rule is enforced identically by
    every decision endpoint instead of being re-implemented (and
    potentially drifting) four times (owner review, PR #101)."""
    plan = await _get_owned_plan(db, user_id, plan_id)
    plan = await _maybe_expire(db, plan)

    if await _is_superseded(db, plan.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=SUPERSEDED_DETAIL)

    _check_source_status(plan, allowed_statuses)

    if extra_check is not None:
        extra_check(plan)

    plan.status = new_status
    plan.decided_at = datetime.now(timezone.utc)
    plan.decision_note = decision_note
    await db.flush()
    await db.refresh(plan)
    return plan


def _require_approvable(plan: TradePlan) -> None:
    math = _compute_risk_reward(plan)
    if not math["multiplier_known"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot approve: '{plan.symbol}' has no verified instrument multiplier, "
                "so dollar risk cannot be validated. Add a multiplier for this symbol before approving."
            ),
        )
    if math["exceeds_max_risk"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot approve: this plan's risk (${math['risk_dollars']}) exceeds its own declared "
                f"max risk (${plan.max_risk_dollars}). Revise the plan with a smaller size/stop, or a "
                "higher declared limit, before approving."
            ),
        )


@router.post("/trade-plans/{plan_id}/approve", response_model=TradePlanRead)
async def approve_trade_plan(
    plan_id: int,
    payload: Optional[TradePlanDecision] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await _decide_plan(
        db,
        current_user.id,
        plan_id,
        "approved",
        payload.decision_note if payload else None,
        extra_check=_require_approvable,
    )
    return await _serialize_plan_live(db, plan)


@router.post("/trade-plans/{plan_id}/reject", response_model=TradePlanRead)
async def reject_trade_plan(
    plan_id: int,
    payload: Optional[TradePlanDecision] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await _decide_plan(db, current_user.id, plan_id, "rejected", payload.decision_note if payload else None)
    return await _serialize_plan_live(db, plan)


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
    plan = await _decide_plan(db, current_user.id, plan_id, "invalidated", payload.decision_note if payload else None)
    return await _serialize_plan_live(db, plan)


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
    plan = await _decide_plan(
        db,
        current_user.id,
        plan_id,
        "canceled",
        payload.decision_note if payload else None,
        allowed_statuses=("pending", "approved"),
    )
    return await _serialize_plan_live(db, plan)


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
    latest revision in a chain may be revised again.

    _is_superseded below is a pre-check, not the real guarantee: two
    concurrent revise requests on the same plan can both pass it before
    either commits. trade_plans.previous_version_id's DB-level unique
    index is what actually prevents the chain from forking; a race that
    reaches the INSERT anyway is caught via IntegrityError below and
    turned into the same 409, instead of silently creating two "latest"
    revisions (owner review, PR #101)."""
    plan = await _get_owned_plan(db, current_user.id, plan_id)
    plan = await _maybe_expire(db, plan)

    if await _is_superseded(db, plan.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=SUPERSEDED_DETAIL)
    if payload.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="expires_at must be in the future")
    broker_account = await _get_owned_broker_account(db, current_user.id, payload.broker_account_id)

    new_plan = _new_plan_from_payload(
        current_user.id,
        payload,
        previous_version_id=plan.id,
        revision_number=plan.revision_number + 1,
        broker_account=broker_account,
    )
    db.add(new_plan)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=SUPERSEDED_DETAIL)

    await db.refresh(new_plan)
    return await _serialize_plan_live(db, new_plan)
