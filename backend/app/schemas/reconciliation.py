"""Request/response schemas for the DF-VS1.5 Step 3A reconciliation
preview (issue #80). This endpoint makes zero database writes -- these
schemas exist purely to validate an input batch and shape a read-only
response; see app.services.reconciliation for the actual logic."""
from __future__ import annotations

from datetime import date as date_type, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ExecutionIn(BaseModel):
    """One broker execution/fill, in the exact field names ProjectX's
    /api/Trade/search returns (see docs/integrations/projectx/
    PROJECTX_API_REFERENCE.md Sec.8 and agent/trader_agent's `trades`
    diagnostic) -- so a batch exported by that diagnostic can be posted
    here with no key renaming. `commissions` is undocumented but real
    (confirmed against a live account, issue #80 PR #88); carried through
    as its own passthrough value, never combined with `fees`."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    account_id: int = Field(alias="accountId")
    contract_id: str = Field(alias="contractId", min_length=1)
    creation_timestamp: datetime = Field(alias="creationTimestamp")
    price: Decimal = Field(gt=0)
    size: int = Field(gt=0)
    side: int
    order_id: Optional[int] = Field(default=None, alias="orderId")
    fees: Optional[Decimal] = Field(default=None, ge=0)
    commissions: Optional[Decimal] = Field(default=None, ge=0)
    profit_and_loss: Optional[Decimal] = Field(default=None, alias="profitAndLoss")
    voided: bool = False


class ReconciliationPreviewRequest(BaseModel):
    account_id: int = Field(gt=0)
    date: date_type
    executions: list[ExecutionIn] = Field(min_length=1)


class ExecutionIdentityOut(BaseModel):
    """Stage 1: broker-reported facts, unmodified."""

    id: int
    order_id: Optional[int]
    contract_id: str
    account_id: int
    creation_timestamp: datetime
    price: Decimal
    size: int
    side: int
    fees: Optional[Decimal]
    commissions: Optional[Decimal]
    broker_profit_and_loss: Optional[Decimal]
    voided: bool
    already_imported: bool
    already_imported_trade_id: Optional[int] = None


GroupingBasis = Literal["shared_order_id", "inferred_open_close_pair", "ungrouped_single", "ambiguous"]
GroupingStatus = Literal["confident", "needs_confirmation"]
PlanMatchStatus = Literal["candidate_match", "ambiguous_candidate_match", "unplanned", "already_imported"]
PnlStatus = Literal["candidate", "unresolved"]


class FillGroupOut(BaseModel):
    """Stage 2 (grouping) + Stage 3 (plan association) for one logical
    group of executions. `plan_match_status` is always a proposal --
    `candidate_match` means exactly one existing plan matched by symbol
    on this date, not a certified/confirmed association."""

    execution_ids: list[int]
    grouping_basis: GroupingBasis
    grouping_status: GroupingStatus
    grouping_note: str

    plan_match_status: PlanMatchStatus
    candidate_trade_ids: list[int]
    plan_match_note: str

    pnl_status: PnlStatus
    candidate_gross_pnl: Optional[Decimal] = None
    pnl_unresolved_reason: Optional[str] = None
    voided: bool = False


class ReconciliationPreviewSummary(BaseModel):
    total_executions: int
    voided_count: int
    already_imported_count: int
    confident_groups: int
    needs_confirmation_groups: int
    candidate_plan_matches: int
    ambiguous_plan_matches: int
    unplanned_groups: int
    groups_with_candidate_pnl: int


class ReconciliationPreviewResponse(BaseModel):
    account_id: int
    date: date_type
    executions: list[ExecutionIdentityOut]
    fill_groups: list[FillGroupOut]
    summary: ReconciliationPreviewSummary
