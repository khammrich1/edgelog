"""DF-VS1.5 Step 3A: read-only broker execution reconciliation preview
(issue #80, owner-approved comment 6240661125).

This endpoint makes ZERO database writes. It accepts a batch of broker
execution rows for one account+date, groups/matches them against the
trader's existing journal data, and returns a preview -- nothing here
creates, updates, or deletes a Trade/TradeEntry/TradeExit row. The actual
"confirm and import" endpoint, the review UI, and the agent-to-cloud
transport are explicitly separate, later, separately-approved slices.
"""
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.journal import TradingDay
from app.models.trades import Trade
from app.models.user import User
from app.schemas.reconciliation import (
    ExecutionIdentityOut,
    FillGroupOut,
    ReconciliationPreviewRequest,
    ReconciliationPreviewResponse,
    ReconciliationPreviewSummary,
)
from app.services.reconciliation import (
    CandidateTrade,
    ExecutionFact,
    build_reconciliation_preview,
)

router = APIRouter()


@router.post("/reconciliation/preview", response_model=ReconciliationPreviewResponse)
async def preview_reconciliation(
    payload: ReconciliationPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    mismatched = [e.id for e in payload.executions if e.account_id != payload.account_id]
    if mismatched:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Execution(s) {mismatched} report a different accountId than the requested "
                f"account_id ({payload.account_id}) -- refusing to mix accounts in one preview."
            ),
        )

    candidate_trades = await _load_candidate_trades(db, current_user.id, payload.date)

    executions = [
        ExecutionFact(
            id=e.id,
            account_id=e.account_id,
            contract_id=e.contract_id,
            creation_timestamp=e.creation_timestamp,
            price=e.price,
            size=e.size,
            side=e.side,
            order_id=e.order_id,
            fees=e.fees,
            commissions=e.commissions,
            broker_profit_and_loss=e.profit_and_loss,
            voided=e.voided,
        )
        for e in payload.executions
    ]

    result = build_reconciliation_preview(executions, candidate_trades)

    executions_out = [
        ExecutionIdentityOut(
            id=r.execution.id,
            order_id=r.execution.order_id,
            contract_id=r.execution.contract_id,
            account_id=r.execution.account_id,
            creation_timestamp=r.execution.creation_timestamp,
            price=r.execution.price,
            size=r.execution.size,
            side=r.execution.side,
            fees=r.execution.fees,
            commissions=r.execution.commissions,
            broker_profit_and_loss=r.execution.broker_profit_and_loss,
            voided=r.execution.voided,
            already_imported=r.already_imported,
            already_imported_trade_id=r.already_imported_trade_id,
        )
        for r in result.executions
    ]

    fill_groups_out = [
        FillGroupOut(
            execution_ids=list(g.execution_ids),
            grouping_basis=g.grouping_basis,
            grouping_status=g.grouping_status,
            grouping_note=g.grouping_note,
            plan_match_status=g.plan_match_status,
            candidate_trade_ids=list(g.candidate_trade_ids),
            plan_match_note=g.plan_match_note,
            pnl_status=g.pnl_status,
            candidate_gross_pnl=g.candidate_gross_pnl,
            pnl_unresolved_reason=g.pnl_unresolved_reason,
            voided=g.voided,
        )
        for g in result.fill_groups
    ]

    summary = ReconciliationPreviewSummary(
        total_executions=len(executions_out),
        voided_count=sum(1 for e in executions_out if e.voided),
        already_imported_count=sum(1 for e in executions_out if e.already_imported),
        confident_groups=sum(1 for g in fill_groups_out if g.grouping_status == "confident"),
        needs_confirmation_groups=sum(1 for g in fill_groups_out if g.grouping_status == "needs_confirmation"),
        candidate_plan_matches=sum(1 for g in fill_groups_out if g.plan_match_status == "candidate_match"),
        ambiguous_plan_matches=sum(1 for g in fill_groups_out if g.plan_match_status == "ambiguous_candidate_match"),
        unplanned_groups=sum(1 for g in fill_groups_out if g.plan_match_status == "unplanned"),
        groups_with_candidate_pnl=sum(1 for g in fill_groups_out if g.pnl_status == "candidate"),
    )

    return ReconciliationPreviewResponse(
        account_id=payload.account_id,
        date=payload.date,
        executions=executions_out,
        fill_groups=fill_groups_out,
        summary=summary,
    )


async def _load_candidate_trades(db: AsyncSession, user_id: int, day: date_type) -> list[CandidateTrade]:
    """Every Trade the user has journaled on this date -- regardless of
    whether it has Plan fields, and regardless of whether it's already
    been reconciled (external_trade_id/external_order_id set) -- the
    service layer buckets those into duplicate-detection vs. open-for-
    matching itself. A pure read; this function never writes."""
    result = await db.execute(
        select(Trade)
        .join(TradingDay, Trade.trading_day_id == TradingDay.id)
        .where(TradingDay.user_id == user_id, TradingDay.date == day)
    )
    trades = result.scalars().all()
    return [
        CandidateTrade(
            id=trade.id,
            symbol=trade.symbol,
            direction=trade.direction,
            setup=trade.setup,
            external_trade_id=trade.external_trade_id,
            external_order_id=trade.external_order_id,
        )
        for trade in trades
    ]
