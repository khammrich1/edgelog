"""Unit tests for the pure reconciliation-preview logic (issue #80 Step
3A). No DB, no HTTP -- fixtures only, matching the service module's own
design goal of being fully testable in isolation."""
from datetime import datetime, timezone
from decimal import Decimal

from app.services.reconciliation import (
    CandidateTrade,
    ExecutionFact,
    build_reconciliation_preview,
    derive_symbol_from_contract_id,
)

CONTRACT_ID = "CON.F.US.MNQ.Z25"


def _execution(id, **overrides):
    defaults = dict(
        account_id=111,
        contract_id=CONTRACT_ID,
        creation_timestamp=datetime(2026, 10, 16, 14, 30, tzinfo=timezone.utc),
        price=Decimal("21000"),
        size=2,
        side=0,
        order_id=None,
        fees=Decimal("2.5"),
        commissions=Decimal("0.62"),
        broker_profit_and_loss=None,
        voided=False,
    )
    defaults.update(overrides)
    return ExecutionFact(id=id, **defaults)


def _trade(id, **overrides):
    defaults = dict(symbol="MNQZ25", direction="long", setup="Breakout", external_trade_id=None, external_order_id=None)
    defaults.update(overrides)
    return CandidateTrade(id=id, **defaults)


def _group_for(result, execution_id):
    return next(g for g in result.fill_groups if execution_id in g.execution_ids)


def test_derive_symbol_from_contract_id_parses_the_documented_shape():
    assert derive_symbol_from_contract_id("CON.F.US.MNQ.Z25") == "MNQZ25"
    assert derive_symbol_from_contract_id("CON.F.US.MGC.G26") == "MGCG26"


def test_derive_symbol_from_contract_id_returns_none_for_unrecognized_shapes():
    assert derive_symbol_from_contract_id("not-a-contract-id") is None
    assert derive_symbol_from_contract_id("") is None


def test_shared_order_id_groups_automatically_and_confidently():
    executions = [
        _execution(1, order_id=500, side=0, creation_timestamp=datetime(2026, 10, 16, 14, 30, tzinfo=timezone.utc)),
        _execution(2, order_id=500, side=0, creation_timestamp=datetime(2026, 10, 16, 14, 31, tzinfo=timezone.utc)),
    ]
    result = build_reconciliation_preview(executions, [])

    group = _group_for(result, 1)
    assert set(group.execution_ids) == {1, 2}
    assert group.grouping_basis == "shared_order_id"
    assert group.grouping_status == "confident"


def test_two_unordered_opposite_side_equal_size_fills_group_as_inferred_pair():
    executions = [
        _execution(1, side=0, size=3, creation_timestamp=datetime(2026, 10, 16, 14, 30, tzinfo=timezone.utc)),
        _execution(2, side=1, size=3, creation_timestamp=datetime(2026, 10, 16, 15, 0, tzinfo=timezone.utc)),
    ]
    result = build_reconciliation_preview(executions, [])

    group = _group_for(result, 1)
    assert set(group.execution_ids) == {1, 2}
    assert group.grouping_basis == "inferred_open_close_pair"
    assert group.grouping_status == "confident"


def test_a_single_unmatched_fill_is_its_own_confident_group_with_unresolved_pnl():
    executions = [_execution(1)]
    result = build_reconciliation_preview(executions, [])

    group = _group_for(result, 1)
    assert group.execution_ids == (1,)
    assert group.grouping_status == "confident"
    assert group.pnl_status == "unresolved"
    assert "two fills" in group.pnl_unresolved_reason.lower()


def test_three_unlinked_fills_on_one_contract_are_each_ambiguous_not_grouped():
    executions = [
        _execution(1, side=0, creation_timestamp=datetime(2026, 10, 16, 14, 30, tzinfo=timezone.utc)),
        _execution(2, side=1, creation_timestamp=datetime(2026, 10, 16, 14, 31, tzinfo=timezone.utc)),
        _execution(3, side=0, creation_timestamp=datetime(2026, 10, 16, 14, 32, tzinfo=timezone.utc)),
    ]
    result = build_reconciliation_preview(executions, [])

    for execution_id in (1, 2, 3):
        group = _group_for(result, execution_id)
        assert group.execution_ids == (execution_id,)
        assert group.grouping_basis == "ambiguous"
        assert group.grouping_status == "needs_confirmation"
        assert group.pnl_status == "unresolved"
        assert group.plan_match_status == "unplanned"
        assert "ambiguous" in group.plan_match_note.lower()


def test_two_same_side_leftover_fills_are_not_inferred_as_a_pair():
    # Same side (both side=0) can't be an open+close pair -- must stay ambiguous.
    executions = [
        _execution(1, side=0, creation_timestamp=datetime(2026, 10, 16, 14, 30, tzinfo=timezone.utc)),
        _execution(2, side=0, creation_timestamp=datetime(2026, 10, 16, 14, 31, tzinfo=timezone.utc)),
    ]
    result = build_reconciliation_preview(executions, [])

    for execution_id in (1, 2):
        group = _group_for(result, execution_id)
        assert group.grouping_basis == "ambiguous"


def test_voided_execution_is_excluded_from_grouping_and_pnl():
    executions = [_execution(1, voided=True)]
    result = build_reconciliation_preview(executions, [])

    assert result.executions[0].execution.voided is True
    group = _group_for(result, 1)
    assert group.voided is True
    assert group.pnl_status == "unresolved"
    assert "voided" in group.pnl_unresolved_reason.lower()
    assert group.plan_match_status == "unplanned"


def test_already_imported_execution_is_detected_by_external_trade_id():
    executions = [_execution(42, order_id=None)]
    trades = [_trade(9, external_trade_id="42")]
    result = build_reconciliation_preview(executions, trades)

    exec_result = result.executions[0]
    assert exec_result.already_imported is True
    assert exec_result.already_imported_trade_id == 9

    group = _group_for(result, 42)
    assert group.plan_match_status == "already_imported"
    assert group.candidate_trade_ids == (9,)
    assert group.pnl_status == "unresolved"


def test_already_imported_execution_is_detected_by_external_order_id():
    executions = [_execution(1, order_id=777), _execution(2, order_id=777)]
    trades = [_trade(9, external_order_id="777")]
    result = build_reconciliation_preview(executions, trades)

    assert all(r.already_imported and r.already_imported_trade_id == 9 for r in result.executions)
    group = _group_for(result, 1)
    assert group.plan_match_status == "already_imported"


def test_unplanned_when_no_candidate_trade_matches_symbol():
    executions = [
        _execution(1, side=0, order_id=1, creation_timestamp=datetime(2026, 10, 16, 14, 30, tzinfo=timezone.utc)),
        _execution(2, side=1, order_id=1, creation_timestamp=datetime(2026, 10, 16, 14, 31, tzinfo=timezone.utc)),
    ]
    result = build_reconciliation_preview(executions, [])

    group = _group_for(result, 1)
    assert group.plan_match_status == "unplanned"
    assert group.candidate_trade_ids == ()
    assert "unplanned" in group.plan_match_note.lower()


def test_candidate_match_when_exactly_one_open_trade_matches_symbol():
    executions = [
        _execution(1, order_id=1, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc), price=Decimal("21000")),
        _execution(2, order_id=1, creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc), price=Decimal("21050")),
    ]
    trades = [_trade(5, symbol="MNQZ25", direction="long")]
    result = build_reconciliation_preview(executions, trades)

    group = _group_for(result, 1)
    assert group.plan_match_status == "candidate_match"
    assert group.candidate_trade_ids == (5,)


def test_candidate_match_resolves_by_root_symbol_even_when_trade_symbol_is_bare_root():
    executions = [
        _execution(1, order_id=1, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc)),
        _execution(2, order_id=1, creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)),
    ]
    trades = [_trade(5, symbol="MNQ")]  # trader logged it without the expiry code
    result = build_reconciliation_preview(executions, trades)

    group = _group_for(result, 1)
    assert group.plan_match_status == "candidate_match"
    assert group.candidate_trade_ids == (5,)


def test_ambiguous_candidate_match_when_multiple_open_trades_match_symbol():
    executions = [
        _execution(1, order_id=1, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc)),
        _execution(2, order_id=1, creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)),
    ]
    trades = [_trade(5), _trade(6)]
    result = build_reconciliation_preview(executions, trades)

    group = _group_for(result, 1)
    assert group.plan_match_status == "ambiguous_candidate_match"
    assert set(group.candidate_trade_ids) == {5, 6}
    assert group.pnl_status == "unresolved"


def test_candidate_gross_pnl_uses_matched_plan_direction_long():
    executions = [
        _execution(1, order_id=1, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc), price=Decimal("21000"), size=2),
        _execution(2, order_id=1, creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc), price=Decimal("21050"), size=2),
    ]
    trades = [_trade(5, direction="long")]
    result = build_reconciliation_preview(executions, trades)

    group = _group_for(result, 1)
    assert group.pnl_status == "candidate"
    # long, entry 21000 -> exit 21050, 50pts * 2 contracts * MNQ multiplier $2 = $200.
    assert group.candidate_gross_pnl == Decimal("200")


def test_candidate_gross_pnl_uses_matched_plan_direction_short():
    executions = [
        _execution(1, order_id=1, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc), price=Decimal("21050"), size=2),
        _execution(2, order_id=1, creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc), price=Decimal("21000"), size=2),
    ]
    trades = [_trade(5, direction="short")]
    result = build_reconciliation_preview(executions, trades)

    group = _group_for(result, 1)
    assert group.pnl_status == "candidate"
    # short, "entry" 21050 -> "exit" 21000 (price dropped 50pts, profit for a short).
    assert group.candidate_gross_pnl == Decimal("200")


def test_candidate_gross_pnl_never_computed_without_an_unambiguous_plan_match():
    executions = [
        _execution(1, order_id=1, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc)),
        _execution(2, order_id=1, creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)),
    ]
    # Unplanned (no trades at all) -- direction is genuinely unknown.
    result = build_reconciliation_preview(executions, [])

    group = _group_for(result, 1)
    assert group.pnl_status == "unresolved"
    assert group.candidate_gross_pnl is None
    assert "side" in group.pnl_unresolved_reason.lower()


def test_candidate_gross_pnl_unresolved_for_unknown_symbol_multiplier():
    executions = [
        _execution(
            1, order_id=1, contract_id="CON.F.US.ZZZ.Z25", creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc)
        ),
        _execution(
            2, order_id=1, contract_id="CON.F.US.ZZZ.Z25", creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)
        ),
    ]
    trades = [_trade(5, symbol="ZZZZ25")]
    result = build_reconciliation_preview(executions, trades)

    group = _group_for(result, 1)
    assert group.pnl_status == "unresolved"
    assert "multiplier" in group.pnl_unresolved_reason.lower()


def test_three_fill_shared_order_group_has_unresolved_pnl_not_invented():
    executions = [
        _execution(1, order_id=1, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc)),
        _execution(2, order_id=1, creation_timestamp=datetime(2026, 10, 16, 9, 31, tzinfo=timezone.utc)),
        _execution(3, order_id=1, creation_timestamp=datetime(2026, 10, 16, 9, 32, tzinfo=timezone.utc)),
    ]
    trades = [_trade(5)]
    result = build_reconciliation_preview(executions, trades)

    group = _group_for(result, 1)
    assert len(group.execution_ids) == 3
    assert group.pnl_status == "unresolved"
    assert "more than two fills" in group.pnl_unresolved_reason.lower()


def test_fees_and_commissions_pass_through_independently_and_uncombined():
    executions = [_execution(1, fees=Decimal("2.50"), commissions=Decimal("0.62"))]
    result = build_reconciliation_preview(executions, [])

    execution_out = result.executions[0].execution
    assert execution_out.fees == Decimal("2.50")
    assert execution_out.commissions == Decimal("0.62")


def test_multiple_executions_from_a_different_account_are_not_filtered_here():
    # Cross-account rejection is the route layer's job (so the service
    # itself stays a pure function of whatever it's given); this just
    # confirms the service doesn't silently drop or merge differing
    # account_id values on its own.
    executions = [_execution(1, account_id=111), _execution(2, account_id=222, order_id=None, side=1, size=2)]
    result = build_reconciliation_preview(executions, [])

    account_ids = {r.execution.account_id for r in result.executions}
    assert account_ids == {111, 222}


def test_duplicate_execution_batches_still_detect_each_already_imported_row():
    executions = [_execution(1, order_id=10), _execution(2, order_id=10)]
    trades = [_trade(9, external_order_id="10")]

    first = build_reconciliation_preview(executions, trades)
    second = build_reconciliation_preview(executions, trades)

    for result in (first, second):
        assert all(r.already_imported for r in result.executions)
