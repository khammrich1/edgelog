"""Unit tests for the pure reconciliation-preview logic (issue #80 Step
3A). No DB, no HTTP -- fixtures only, matching the service module's own
design goal of being fully testable in isolation."""
from datetime import date, datetime, timezone
from decimal import Decimal

from app.services.reconciliation import (
    CandidateTrade,
    ExecutionFact,
    build_reconciliation_preview,
    derive_symbol_from_contract_id,
)

CONTRACT_ID = "CON.F.US.MNQ.Z25"
REQUESTED_DATE = date(2026, 10, 16)
ACCOUNT_ID = 111


def _execution(id, **overrides):
    defaults = dict(
        account_id=ACCOUNT_ID,
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
    defaults = dict(
        symbol="MNQZ25",
        direction="long",
        setup="Breakout",
        external_trade_id=None,
        external_order_id=None,
        account_id=None,
        entry_date=REQUESTED_DATE,
    )
    defaults.update(overrides)
    return CandidateTrade(id=id, **defaults)


def _preview(executions, trades=(), account_id=ACCOUNT_ID, requested_date=REQUESTED_DATE):
    return build_reconciliation_preview(executions, list(trades), account_id, requested_date)


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
    result = _preview(executions)

    group = _group_for(result, 1)
    assert set(group.execution_ids) == {1, 2}
    assert group.grouping_basis == "shared_order_id"
    assert group.grouping_status == "confident"


def test_inferred_open_close_pair_needs_confirmation_not_confident():
    # Review finding (PR #91): two unrelated executions could coincidentally
    # share opposite sides and equal size with no orderId -- this is a
    # plausible guess, not a verified identifier match, so it must never
    # be auto-certified as a confident grouping.
    executions = [
        _execution(1, side=0, size=3, creation_timestamp=datetime(2026, 10, 16, 14, 30, tzinfo=timezone.utc)),
        _execution(2, side=1, size=3, creation_timestamp=datetime(2026, 10, 16, 15, 0, tzinfo=timezone.utc)),
    ]
    result = _preview(executions)

    group = _group_for(result, 1)
    assert set(group.execution_ids) == {1, 2}
    assert group.grouping_basis == "inferred_open_close_pair"
    assert group.grouping_status == "needs_confirmation"
    assert group.pnl_status == "unresolved"
    assert group.plan_match_status == "unplanned"
    assert "ambiguous" in group.plan_match_note.lower()


def test_a_single_unmatched_fill_is_its_own_confident_group_with_unresolved_pnl():
    executions = [_execution(1)]
    result = _preview(executions)

    group = _group_for(result, 1)
    assert group.execution_ids == (1,)
    assert group.grouping_status == "confident"
    assert group.pnl_status == "unresolved"
    # Issue #104: observed on public DEV via the safe fixture -- a group
    # of exactly one fill was previously (wrongly) given the ">2 fills"
    # reason, which is false for a group this small. It must instead say
    # there's no counterpart fill yet, never claim there are "more than
    # two fills" (this assertion used to read "two fills" in the reason,
    # which passed only because "more than two fills" happens to contain
    # that substring -- it was unknowingly asserting the bug).
    reason = group.pnl_unresolved_reason.lower()
    assert "more than two fills" not in reason
    assert "one fill" in reason
    assert "counterpart" in reason


def test_three_unlinked_fills_on_one_contract_are_each_ambiguous_not_grouped():
    executions = [
        _execution(1, side=0, creation_timestamp=datetime(2026, 10, 16, 14, 30, tzinfo=timezone.utc)),
        _execution(2, side=1, creation_timestamp=datetime(2026, 10, 16, 14, 31, tzinfo=timezone.utc)),
        _execution(3, side=0, creation_timestamp=datetime(2026, 10, 16, 14, 32, tzinfo=timezone.utc)),
    ]
    result = _preview(executions)

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
    result = _preview(executions)

    for execution_id in (1, 2):
        group = _group_for(result, execution_id)
        assert group.grouping_basis == "ambiguous"


def test_voided_execution_is_excluded_from_grouping_and_pnl():
    executions = [_execution(1, voided=True)]
    result = _preview(executions)

    assert result.executions[0].execution.voided is True
    group = _group_for(result, 1)
    assert group.voided is True
    assert group.pnl_status == "unresolved"
    assert "voided" in group.pnl_unresolved_reason.lower()
    assert group.plan_match_status == "unplanned"


def test_already_imported_execution_is_detected_by_external_trade_id():
    executions = [_execution(42, order_id=None)]
    trades = [_trade(9, external_trade_id="42")]
    result = _preview(executions, trades)

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
    result = _preview(executions, trades)

    assert all(r.already_imported and r.already_imported_trade_id == 9 for r in result.executions)
    group = _group_for(result, 1)
    assert group.plan_match_status == "already_imported"


def test_already_imported_detection_is_not_scoped_to_the_requested_date():
    # Review finding (PR #91): a broker execution ID is a fact independent
    # of which date a preview is run for -- a prior import filed under a
    # different date must still be found, not missed because it's "not
    # today's trade".
    executions = [_execution(1, order_id=777)]
    trades = [_trade(9, external_order_id="777", entry_date=date(2020, 1, 1))]
    result = _preview(executions, trades, requested_date=REQUESTED_DATE)

    assert result.executions[0].already_imported is True
    assert result.executions[0].already_imported_trade_id == 9


def test_unplanned_when_no_candidate_trade_matches_symbol():
    executions = [
        _execution(1, side=0, order_id=1, creation_timestamp=datetime(2026, 10, 16, 14, 30, tzinfo=timezone.utc)),
        _execution(2, side=1, order_id=1, creation_timestamp=datetime(2026, 10, 16, 14, 31, tzinfo=timezone.utc)),
    ]
    result = _preview(executions)

    group = _group_for(result, 1)
    assert group.plan_match_status == "unplanned"
    assert group.candidate_trade_ids == ()
    # Issue #104: the note must describe this accurately as "no journal
    # Trade candidate found" -- never claim a plan was looked for (this
    # preview matches existing journal Trade records, not TradePlan
    # objects) or that anything would be imported (this endpoint never
    # imports).
    assert "journal trade" in group.plan_match_note.lower()
    assert "plan" not in group.plan_match_note.lower()
    assert "would import" not in group.plan_match_note.lower()


def test_candidate_match_when_exactly_one_open_trade_matches_symbol():
    executions = [
        _execution(1, order_id=1, side=0, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc), price=Decimal("21000")),
        _execution(2, order_id=1, side=1, creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc), price=Decimal("21050")),
    ]
    trades = [_trade(5, symbol="MNQZ25", direction="long")]
    result = _preview(executions, trades)

    group = _group_for(result, 1)
    assert group.plan_match_status == "candidate_match"
    assert group.candidate_trade_ids == (5,)


def test_candidate_match_resolves_by_root_symbol_even_when_trade_symbol_is_bare_root():
    executions = [
        _execution(1, order_id=1, side=0, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc)),
        _execution(2, order_id=1, side=1, creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)),
    ]
    trades = [_trade(5, symbol="MNQ")]  # trader logged it without the expiry code
    result = _preview(executions, trades)

    group = _group_for(result, 1)
    assert group.plan_match_status == "candidate_match"
    assert group.candidate_trade_ids == (5,)


def test_candidate_match_requires_the_trade_to_be_on_the_requested_date():
    # Review finding (PR #91): fresh plan-match candidates must be scoped
    # to the exact requested date -- a symbol-matching Trade from a
    # different day is not a candidate here.
    executions = [
        _execution(1, order_id=1, side=0, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc)),
        _execution(2, order_id=1, side=1, creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)),
    ]
    trades = [_trade(5, entry_date=date(2026, 10, 15))]
    result = _preview(executions, trades)

    group = _group_for(result, 1)
    assert group.plan_match_status == "unplanned"
    assert group.candidate_trade_ids == ()


def test_candidate_match_excludes_a_trade_known_to_belong_to_a_different_account():
    # Review finding (PR #91): candidate matching must be scoped to the
    # requested broker account, not just user/date.
    executions = [
        _execution(1, order_id=1, side=0, account_id=111, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc)),
        _execution(2, order_id=1, side=1, account_id=111, creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)),
    ]
    trades = [_trade(5, account_id="999999")]
    result = _preview(executions, trades, account_id=111)

    group = _group_for(result, 1)
    assert group.plan_match_status == "unplanned"
    assert group.candidate_trade_ids == ()


def test_candidate_match_includes_a_trade_with_no_account_id_recorded_for_any_account():
    # A Trade logged before account tracking existed (account_id is None)
    # must remain matchable regardless of which account is requested --
    # it predates the distinction, it isn't known to belong elsewhere.
    executions = [
        _execution(1, order_id=1, side=0, account_id=222, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc)),
        _execution(2, order_id=1, side=1, account_id=222, creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)),
    ]
    trades = [_trade(5, account_id=None)]
    result = _preview(executions, trades, account_id=222)

    group = _group_for(result, 1)
    assert group.plan_match_status == "candidate_match"
    assert group.candidate_trade_ids == (5,)


def test_candidate_match_includes_a_trade_whose_account_id_matches_exactly():
    executions = [
        _execution(1, order_id=1, side=0, account_id=222, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc)),
        _execution(2, order_id=1, side=1, account_id=222, creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)),
    ]
    trades = [_trade(5, account_id="222")]
    result = _preview(executions, trades, account_id=222)

    group = _group_for(result, 1)
    assert group.plan_match_status == "candidate_match"
    assert group.candidate_trade_ids == (5,)


def test_ambiguous_candidate_match_when_multiple_open_trades_match_symbol():
    executions = [
        _execution(1, order_id=1, side=0, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc)),
        _execution(2, order_id=1, side=1, creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)),
    ]
    trades = [_trade(5), _trade(6)]
    result = _preview(executions, trades)

    group = _group_for(result, 1)
    assert group.plan_match_status == "ambiguous_candidate_match"
    assert set(group.candidate_trade_ids) == {5, 6}
    assert group.pnl_status == "unresolved"


def test_candidate_gross_pnl_uses_matched_plan_direction_long():
    executions = [
        _execution(
            1, order_id=1, side=0, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc), price=Decimal("21000"), size=2
        ),
        _execution(
            2, order_id=1, side=1, creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc), price=Decimal("21050"), size=2
        ),
    ]
    trades = [_trade(5, direction="long")]
    result = _preview(executions, trades)

    group = _group_for(result, 1)
    assert group.pnl_status == "candidate"
    # long, entry 21000 -> exit 21050, 50pts * 2 contracts * MNQ multiplier $2 = $200.
    assert group.candidate_gross_pnl == Decimal("200")


def test_candidate_gross_pnl_uses_matched_plan_direction_short():
    executions = [
        _execution(
            1, order_id=1, side=0, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc), price=Decimal("21050"), size=2
        ),
        _execution(
            2, order_id=1, side=1, creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc), price=Decimal("21000"), size=2
        ),
    ]
    trades = [_trade(5, direction="short")]
    result = _preview(executions, trades)

    group = _group_for(result, 1)
    assert group.pnl_status == "candidate"
    # short, "entry" 21050 -> "exit" 21000 (price dropped 50pts, profit for a short).
    assert group.candidate_gross_pnl == Decimal("200")


def test_candidate_gross_pnl_never_computed_without_an_unambiguous_plan_match():
    executions = [
        _execution(1, order_id=1, side=0, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc)),
        _execution(2, order_id=1, side=1, creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)),
    ]
    # Unplanned (no trades at all) -- direction is genuinely unknown.
    result = _preview(executions)

    group = _group_for(result, 1)
    assert group.pnl_status == "unresolved"
    assert group.candidate_gross_pnl is None
    assert "side" in group.pnl_unresolved_reason.lower()


def test_candidate_gross_pnl_unresolved_for_unknown_symbol_multiplier():
    executions = [
        _execution(
            1,
            order_id=1,
            side=0,
            contract_id="CON.F.US.ZZZ.Z25",
            creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc),
        ),
        _execution(
            2,
            order_id=1,
            side=1,
            contract_id="CON.F.US.ZZZ.Z25",
            creation_timestamp=datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc),
        ),
    ]
    trades = [_trade(5, symbol="ZZZZ25")]
    result = _preview(executions, trades)

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
    result = _preview(executions, trades)

    group = _group_for(result, 1)
    assert len(group.execution_ids) == 3
    assert group.pnl_status == "unresolved"
    assert "more than two fills" in group.pnl_unresolved_reason.lower()


def test_two_fills_sharing_an_order_id_with_the_same_side_never_get_a_pnl():
    # The core review finding (PR #91): a shared orderId groups fills
    # together, but an order's own fills all share that order's side --
    # two same-side fills are one leg of a position (e.g. two partial
    # entries), never a verified round trip, even with a matched plan.
    executions = [
        _execution(1, order_id=1, side=0, creation_timestamp=datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc), price=Decimal("21000")),
        _execution(2, order_id=1, side=0, creation_timestamp=datetime(2026, 10, 16, 9, 31, tzinfo=timezone.utc), price=Decimal("21010")),
    ]
    trades = [_trade(5, direction="long")]
    result = _preview(executions, trades)

    group = _group_for(result, 1)
    assert group.grouping_status == "confident"  # the fills ARE verifiably related
    assert group.plan_match_status == "candidate_match"  # a plan match can still be proposed
    assert group.pnl_status == "unresolved"  # but P&L must not be invented from one leg
    assert group.candidate_gross_pnl is None
    assert "same side" in group.pnl_unresolved_reason.lower()


def test_fees_and_commissions_pass_through_independently_and_uncombined():
    executions = [_execution(1, fees=Decimal("2.50"), commissions=Decimal("0.62"))]
    result = _preview(executions)

    execution_out = result.executions[0].execution
    assert execution_out.fees == Decimal("2.50")
    assert execution_out.commissions == Decimal("0.62")


def test_multiple_executions_from_a_different_account_are_not_filtered_here():
    # Cross-account rejection is the route layer's job (so the service
    # itself stays a pure function of whatever it's given); this just
    # confirms the service doesn't silently drop or merge differing
    # account_id values on its own.
    executions = [_execution(1, account_id=111), _execution(2, account_id=222, order_id=None, side=1, size=2)]
    result = _preview(executions, account_id=111)

    account_ids = {r.execution.account_id for r in result.executions}
    assert account_ids == {111, 222}


def test_duplicate_execution_batches_still_detect_each_already_imported_row():
    executions = [_execution(1, order_id=10), _execution(2, order_id=10)]
    trades = [_trade(9, external_order_id="10")]

    first = _preview(executions, trades)
    second = _preview(executions, trades)

    for result in (first, second):
        assert all(r.already_imported for r in result.executions)
