"""Pure matching/grouping/P&L logic for DF-VS1.5 Step 3A: the read-only
reconciliation preview (issue #80, owner-approved comment 6240661125).

Nothing here touches the database or FastAPI -- the route handler does the
one DB read (existing Trades for this user/account/date) and translates to
and from these plain dataclasses, so this module is fully unit-testable
with fixtures and carries zero risk of an accidental write. That split is
deliberate: this is the one piece of logic in the whole slice with real
consequences if it's wrong, so it's also the one piece kept smallest and
most directly testable.

Three distinct stages, per the owner's correction (issue #80 chat,
2026-10-17) -- never blurred together:

1. Broker execution identity -- facts straight off the wire (id, orderId,
   accountId, price, size, ...). Always certain; nothing to resolve.
2. Fill grouping -- which executions belong to the same logical trade.
   Automatic ONLY when a shared orderId, or an unambiguous 2-fill
   opposite-side same-size pair, makes it deterministic. Anything else is
   `needs_confirmation`, never guessed.
3. Journal plan association -- always a PROPOSAL for trader review, never
   an automatic certification, even when exactly one candidate matches.

Candidate gross P&L deliberately does NOT trust the broker's per-fill
`profitAndLoss` (unreliable per the real DEV test: 23/39 present) and does
NOT guess at the broker's `side` encoding (Buy/Sell mapping unconfirmed,
per agent/README.md). Instead, it borrows the DIRECTION from an
unambiguous matched Plan (trader-entered, already trusted) and computes
from chronological entry/exit prices -- if there is no single unambiguous
plan match, direction is genuinely unknowable here, and P&L is marked
`unresolved`, never invented.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.core.instruments import get_multiplier

# ProjectX's contractId (e.g. "CON.F.US.MNQ.Z25") is not a bare symbol --
# EdgeLog's get_multiplier expects a dated contract shaped like "MNQZ25".
# This mirrors app.core.instruments._DATED_CONTRACT_RE's month-code set;
# duplicated rather than imported since that name is private to that
# module and this is a distinct parsing concern (a provider's contract ID
# format, not EdgeLog's own dated-contract convention).
_CONTRACT_MONTH_CODES = "FGHJKMNQUVXZ"
_CONTRACT_ID_RE = re.compile(rf"^CON\.[A-Z]\.[A-Z]{{2}}\.([A-Z0-9]{{1,3}})\.([{_CONTRACT_MONTH_CODES}]\d{{1,4}})$")


def derive_symbol_from_contract_id(contract_id: str) -> Optional[str]:
    """Returns an EdgeLog-shaped dated-contract symbol (e.g. "MNQZ25") for
    a ProjectX contractId, or None for any shape not matching this
    specific documented pattern -- never a guess at the root."""
    match = _CONTRACT_ID_RE.match(contract_id.strip().upper())
    if not match:
        return None
    root, month_year = match.groups()
    return f"{root}{month_year}"


def _root_symbol(symbol: str) -> str:
    """Strips a dated contract's month-code+year suffix, if present, so a
    manually-logged Trade.symbol of "MNQ" still matches an execution whose
    derived symbol is "MNQZ25". Returns the input unchanged if it isn't in
    that dated shape (already a bare root, or an unrecognized format)."""
    normalized = symbol.strip().upper()
    match = re.match(rf"^([A-Z]{{1,3}})[{_CONTRACT_MONTH_CODES}]\d{{1,4}}$", normalized)
    return match.group(1) if match else normalized


@dataclass(frozen=True)
class ExecutionFact:
    """Stage 1: broker-reported facts for one execution/fill. Carries
    `commissions` as its own passthrough value, per the owner's explicit
    instruction not to assume its relationship to `fees` or add them
    together -- this slice stores and surfaces it, nothing more."""

    id: int
    account_id: int
    contract_id: str
    creation_timestamp: datetime
    price: Decimal
    size: int
    side: int
    order_id: Optional[int] = None
    fees: Optional[Decimal] = None
    commissions: Optional[Decimal] = None
    broker_profit_and_loss: Optional[Decimal] = None
    voided: bool = False


@dataclass(frozen=True)
class CandidateTrade:
    """A Trade already in the journal for this user, on the requested
    date, eligible to be proposed as a plan match. `external_trade_id`/
    `external_order_id` being set means this Trade was already reconciled
    to a specific broker execution -- used for duplicate detection, not
    offered as a fresh candidate."""

    id: int
    symbol: str
    direction: str  # "long" | "short"
    setup: Optional[str]
    external_trade_id: Optional[str]
    external_order_id: Optional[str]


@dataclass(frozen=True)
class ExecutionResult:
    execution: ExecutionFact
    already_imported: bool
    already_imported_trade_id: Optional[int] = None


@dataclass(frozen=True)
class FillGroupResult:
    execution_ids: tuple[int, ...]
    grouping_basis: str  # "shared_order_id" | "inferred_open_close_pair" | "ungrouped_single" | "ambiguous"
    grouping_status: str  # "confident" | "needs_confirmation"
    grouping_note: str

    plan_match_status: str  # "candidate_match" | "ambiguous_candidate_match" | "unplanned" | "already_imported"
    candidate_trade_ids: tuple[int, ...]
    plan_match_note: str

    pnl_status: str  # "candidate" | "unresolved"
    candidate_gross_pnl: Optional[Decimal] = None
    pnl_unresolved_reason: Optional[str] = None
    voided: bool = False


@dataclass(frozen=True)
class ReconciliationPreviewResult:
    executions: tuple[ExecutionResult, ...]
    fill_groups: tuple[FillGroupResult, ...]


def _already_imported_trade_id(execution: ExecutionFact, candidate_trades: list[CandidateTrade]) -> Optional[int]:
    execution_id_str = str(execution.id)
    order_id_str = str(execution.order_id) if execution.order_id is not None else None
    for trade in candidate_trades:
        if trade.external_trade_id is not None and trade.external_trade_id == execution_id_str:
            return trade.id
        if order_id_str is not None and trade.external_order_id is not None and trade.external_order_id == order_id_str:
            return trade.id
    return None


def _group_fresh_executions(executions: list[ExecutionFact]) -> list[tuple[tuple[int, ...], str, str, str]]:
    """Groups non-voided, not-already-imported executions sharing a
    contract. Returns (execution_ids, basis, status, note) tuples. The
    only two groupings ever treated as automatic/confident:
    (a) every execution sharing one non-null order_id, (b) exactly two
    leftover executions on the same contract with opposite `side` values
    and equal `size` (an unambiguous open+close pair). Anything else is
    left ungrouped and flagged ambiguous -- never further guessed at."""
    groups: list[tuple[tuple[int, ...], str, str, str]] = []

    by_contract: dict[str, list[ExecutionFact]] = {}
    for execution in executions:
        by_contract.setdefault(execution.contract_id, []).append(execution)

    for contract_executions in by_contract.values():
        by_order: dict[int, list[ExecutionFact]] = {}
        leftover: list[ExecutionFact] = []
        for execution in contract_executions:
            if execution.order_id is not None:
                by_order.setdefault(execution.order_id, []).append(execution)
            else:
                leftover.append(execution)

        for order_id, fills in by_order.items():
            ids = tuple(sorted(f.id for f in fills))
            groups.append(
                (
                    ids,
                    "shared_order_id",
                    "confident",
                    f"Grouped automatically: all {len(ids)} fill(s) share broker orderId {order_id}.",
                )
            )

        # Pair off leftover (no orderId) executions two at a time only
        # when the pairing is completely unambiguous: exactly two
        # executions left with opposite side values and equal size.
        remaining = list(leftover)
        if len(remaining) == 2 and remaining[0].side != remaining[1].side and remaining[0].size == remaining[1].size:
            ids = tuple(sorted(f.id for f in remaining))
            groups.append(
                (
                    ids,
                    "inferred_open_close_pair",
                    "confident",
                    "Grouped automatically: exactly two fills with opposite side values and matching "
                    "size, and no orderId to group by -- treated as one open+close pair.",
                )
            )
        elif len(remaining) == 1:
            ids = (remaining[0].id,)
            groups.append(
                (
                    ids,
                    "ungrouped_single",
                    "confident",
                    "Single fill with no orderId and no matching counterpart in this batch -- "
                    "treated as its own group (e.g. a position opened but not yet closed here).",
                )
            )
        elif remaining:
            # 3+ leftover fills with no orderId, or a 2-fill leftover that
            # isn't a clean opposite-side/equal-size pair: never guessed.
            for execution in remaining:
                groups.append(
                    (
                        (execution.id,),
                        "ambiguous",
                        "needs_confirmation",
                        "Could not determine this fill's grouping automatically (no orderId, and no "
                        "unambiguous 2-fill pairing available) -- needs trader confirmation.",
                    )
                )

    return groups


def _find_candidate_trades(symbol: Optional[str], candidate_trades: list[CandidateTrade]) -> list[CandidateTrade]:
    if symbol is None:
        return []
    root = _root_symbol(symbol)
    openable = [t for t in candidate_trades if t.external_trade_id is None and t.external_order_id is None]
    return [t for t in openable if _root_symbol(t.symbol) == root]


def build_reconciliation_preview(
    executions: list[ExecutionFact],
    candidate_trades: list[CandidateTrade],
) -> ReconciliationPreviewResult:
    execution_results: list[ExecutionResult] = []
    already_imported_by_id: dict[int, Optional[int]] = {}
    for execution in executions:
        trade_id = _already_imported_trade_id(execution, candidate_trades)
        already_imported_by_id[execution.id] = trade_id
        execution_results.append(
            ExecutionResult(execution=execution, already_imported=trade_id is not None, already_imported_trade_id=trade_id)
        )

    by_id = {e.id: e for e in executions}
    fill_groups: list[FillGroupResult] = []

    voided = [e for e in executions if e.voided]
    already_imported = [e for e in executions if not e.voided and already_imported_by_id[e.id] is not None]
    fresh = [e for e in executions if not e.voided and already_imported_by_id[e.id] is None]

    for execution in voided:
        fill_groups.append(
            FillGroupResult(
                execution_ids=(execution.id,),
                grouping_basis="ungrouped_single",
                grouping_status="needs_confirmation",
                grouping_note="Voided execution -- excluded from automatic grouping and P&L; needs manual review.",
                plan_match_status="unplanned",
                candidate_trade_ids=(),
                plan_match_note="Voided executions are not proposed against any plan.",
                pnl_status="unresolved",
                pnl_unresolved_reason="Execution is voided; a voided fill never contributes to P&L.",
                voided=True,
            )
        )

    for execution in already_imported:
        trade_id = already_imported_by_id[execution.id]
        fill_groups.append(
            FillGroupResult(
                execution_ids=(execution.id,),
                grouping_basis="ungrouped_single",
                grouping_status="confident",
                grouping_note="Matched an existing external trade/order ID -- already reconciled previously.",
                plan_match_status="already_imported",
                candidate_trade_ids=(trade_id,) if trade_id is not None else (),
                plan_match_note=f"Already reconciled to existing Trade #{trade_id} by external ID match.",
                pnl_status="unresolved",
                pnl_unresolved_reason="Already imported; this preview does not recompute P&L for past imports.",
            )
        )

    for execution_ids, basis, status, note in _group_fresh_executions(fresh):
        group_executions = [by_id[i] for i in execution_ids]
        symbols = {derive_symbol_from_contract_id(e.contract_id) for e in group_executions}
        symbol = next(iter(symbols)) if len(symbols) == 1 else None

        candidates = _find_candidate_trades(symbol, candidate_trades) if status == "confident" else []
        if len(candidates) == 1:
            plan_match_status = "candidate_match"
            candidate_ids = (candidates[0].id,)
            plan_match_note = (
                f"Proposed by matching symbol against Trade #{candidates[0].id} on this date -- "
                "review before confirming; not an automatic match by broker ID."
            )
        elif len(candidates) > 1:
            plan_match_status = "ambiguous_candidate_match"
            candidate_ids = tuple(sorted(t.id for t in candidates))
            plan_match_note = (
                f"{len(candidates)} existing trades match this symbol/date -- trader must choose; not auto-resolved."
            )
        else:
            plan_match_status = "unplanned"
            candidate_ids = ()
            plan_match_note = (
                "No existing plan found for this symbol/date -- would import as "
                "Unplanned / No pre-trade plan recorded."
                if status == "confident"
                else "Grouping is ambiguous, so no plan match was attempted."
            )

        pnl_status, gross_pnl, unresolved_reason = _candidate_pnl(
            group_executions, basis, status, symbol, plan_match_status, candidates
        )

        fill_groups.append(
            FillGroupResult(
                execution_ids=execution_ids,
                grouping_basis=basis,
                grouping_status=status,
                grouping_note=note,
                plan_match_status=plan_match_status,
                candidate_trade_ids=candidate_ids,
                plan_match_note=plan_match_note,
                pnl_status=pnl_status,
                candidate_gross_pnl=gross_pnl,
                pnl_unresolved_reason=unresolved_reason,
            )
        )

    return ReconciliationPreviewResult(executions=tuple(execution_results), fill_groups=tuple(fill_groups))


def _candidate_pnl(
    group_executions: list[ExecutionFact],
    basis: str,
    grouping_status: str,
    symbol: Optional[str],
    plan_match_status: str,
    candidates: list[CandidateTrade],
) -> tuple[str, Optional[Decimal], Optional[str]]:
    """Computes candidate gross P&L ONLY for the single case this slice
    trusts completely: a confidently-grouped pair of exactly two fills,
    matched to exactly one existing plan (so direction is a trusted,
    trader-entered fact, never guessed from the broker's unconfirmed
    `side` encoding), on a symbol with a verified multiplier. Every other
    shape is explicitly unresolved, with the specific reason -- never an
    invented number."""
    if grouping_status != "confident":
        return "unresolved", None, "Fill grouping is ambiguous; group manually before P&L can be computed."
    if len(group_executions) != 2:
        return (
            "unresolved",
            None,
            "Group has more than two fills; multi-fill P&L aggregation isn't implemented in this preview slice.",
        )
    if plan_match_status != "candidate_match":
        return (
            "unresolved",
            None,
            "No single unambiguous plan match to source direction from -- the broker's `side` encoding "
            "is not independently confirmed, so direction can't be assumed.",
        )
    if symbol is None:
        return "unresolved", None, "Could not derive a known contract symbol from this execution's contractId."

    multiplier = get_multiplier(symbol)
    if multiplier is None:
        return "unresolved", None, f"No verified per-point multiplier for symbol '{symbol}'."

    direction = candidates[0].direction
    sign = Decimal(1) if direction == "long" else Decimal(-1)
    ordered = sorted(group_executions, key=lambda e: e.creation_timestamp)
    entry_fill, exit_fill = ordered[0], ordered[1]
    size = entry_fill.size

    movement = (exit_fill.price - entry_fill.price) * sign
    gross_pnl = movement * size * multiplier
    return "candidate", gross_pnl, None
