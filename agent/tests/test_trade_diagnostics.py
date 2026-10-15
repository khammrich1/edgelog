from datetime import datetime, timezone

import pytest

from trader_agent.providers.base import TradeRecord
from trader_agent.trade_diagnostics import (
    DOCUMENTED_TRADE_FIELDS,
    format_report,
    parse_flexible_datetime,
    redact_identifier,
    summarize_trade_records,
    to_utc_iso,
)


def _record(raw: dict) -> TradeRecord:
    return TradeRecord(
        id=raw.get("id"),
        account_id=raw.get("accountId"),
        contract_id=raw.get("contractId"),
        creation_timestamp=raw.get("creationTimestamp"),
        price=raw.get("price"),
        profit_and_loss=raw.get("profitAndLoss"),
        fees=raw.get("fees"),
        side=raw.get("side"),
        size=raw.get("size"),
        voided=raw.get("voided"),
        order_id=raw.get("orderId"),
        raw=raw,
    )


# Sanitized fixture: a full response matching the documented shape exactly.
FULL_SHAPE_RAW = {
    "id": 1001,
    "accountId": 222222,
    "contractId": "CON.F.US.MNQ.Z25",
    "creationTimestamp": "2026-10-01T14:30:00Z",
    "price": 21005.5,
    "profitAndLoss": 38.0,
    "fees": 2.5,
    "side": 0,
    "size": 2,
    "voided": False,
    "orderId": 5551,
}


def test_summarize_reports_every_documented_field_present_for_a_full_shape_record():
    report = summarize_trade_records([_record(FULL_SHAPE_RAW)])

    assert report.total_records == 1
    by_field = {obs.field: obs for obs in report.field_observations}
    for field_name in DOCUMENTED_TRADE_FIELDS:
        assert by_field[field_name].present_count == 1, f"{field_name} should be reported present"
    assert report.unexpected_fields == ()


def test_summarize_never_surfaces_identifier_or_monetary_values_in_the_report_object():
    report = summarize_trade_records([_record(FULL_SHAPE_RAW)])

    serialized = repr(report)
    assert "222222" not in serialized  # accountId value
    assert "5551" not in serialized  # orderId value
    assert "21005.5" not in serialized  # price value
    assert "38.0" not in serialized  # profitAndLoss value


def test_summarize_marks_identifier_and_monetary_fields_as_redacted():
    report = summarize_trade_records([_record(FULL_SHAPE_RAW)])
    by_field = {obs.field: obs for obs in report.field_observations}

    for field_name in ("id", "accountId", "contractId", "orderId", "price", "profitAndLoss", "fees"):
        assert by_field[field_name].redacted is True
    for field_name in ("side", "voided", "creationTimestamp", "size"):
        assert by_field[field_name].redacted is False


def test_summarize_captures_distinct_values_for_side_and_voided_only():
    records = [
        _record({**FULL_SHAPE_RAW, "side": 0, "voided": False}),
        _record({**FULL_SHAPE_RAW, "side": 1, "voided": False}),
    ]
    report = summarize_trade_records(records)
    by_field = {obs.field: obs for obs in report.field_observations}

    assert set(by_field["side"].distinct_values) == {0, 1}
    assert set(by_field["voided"].distinct_values) == {False}
    assert by_field["price"].distinct_values is None


def test_summarize_detects_missing_documented_fields():
    sparse_raw = {"id": 1, "accountId": 222222, "price": 21005.5}
    report = summarize_trade_records([_record(sparse_raw)])
    by_field = {obs.field: obs for obs in report.field_observations}

    assert by_field["fees"].present_count == 0
    assert by_field["voided"].present_count == 0
    assert by_field["profitAndLoss"].present_count == 0


def test_summarize_detects_undocumented_fields_in_a_live_response():
    surprising_raw = {**FULL_SHAPE_RAW, "commission": 1.25, "exchangeFee": 0.5}
    report = summarize_trade_records([_record(surprising_raw)])

    assert set(report.unexpected_fields) == {"commission", "exchangeFee"}


def test_summarize_treats_null_values_the_same_as_absent_keys():
    raw_with_nulls = {**FULL_SHAPE_RAW, "fees": None, "voided": None}
    report = summarize_trade_records([_record(raw_with_nulls)])
    by_field = {obs.field: obs for obs in report.field_observations}

    assert by_field["fees"].present_count == 0
    assert by_field["voided"].present_count == 0


def test_summarize_empty_record_list_reports_zero_total():
    report = summarize_trade_records([])

    assert report.total_records == 0
    assert all(obs.present_count == 0 for obs in report.field_observations)


def test_commission_fee_finding_notes_the_single_undifferentiated_fees_field():
    report = summarize_trade_records([_record(FULL_SHAPE_RAW)])

    assert "commission" in report.commission_fee_finding.lower()
    assert "fees" in report.commission_fee_finding.lower()


def test_format_report_never_prints_the_redacted_values():
    report = summarize_trade_records([_record(FULL_SHAPE_RAW)])
    text = format_report(report)

    assert "222222" not in text
    assert "5551" not in text
    assert "21005.5" not in text
    assert "value redacted" in text


def test_format_report_shows_observed_side_and_voided_values():
    records = [_record({**FULL_SHAPE_RAW, "side": 0}), _record({**FULL_SHAPE_RAW, "side": 1})]
    text = format_report(summarize_trade_records(records))

    assert "observed values:" in text


def test_format_report_flags_unexpected_identifier_shaped_fields():
    surprising_raw = {**FULL_SHAPE_RAW, "clearingFeeId": 99}
    text = format_report(summarize_trade_records([_record(surprising_raw)]))

    assert "clearingFeeId" in text
    assert "treat as sensitive" in text


def test_redact_identifier_never_returns_the_original_value():
    assert redact_identifier(222222) != "222222"
    assert redact_identifier(222222).endswith("22")
    assert "2222" not in redact_identifier(222222)


def test_redact_identifier_handles_short_values():
    assert redact_identifier(5) == "*"


def test_to_utc_iso_assumes_naive_datetimes_are_already_utc():
    assert to_utc_iso(datetime(2026, 10, 1, 12, 0, 0)) == "2026-10-01T12:00:00+00:00"


def test_to_utc_iso_converts_an_aware_non_utc_datetime():
    from datetime import timedelta

    eastern = timezone(timedelta(hours=-4))
    assert to_utc_iso(datetime(2026, 10, 1, 8, 0, 0, tzinfo=eastern)) == "2026-10-01T12:00:00+00:00"


def test_parse_flexible_datetime_accepts_a_bare_date():
    parsed = parse_flexible_datetime("2026-10-01")
    assert parsed == datetime(2026, 10, 1, tzinfo=timezone.utc)


def test_parse_flexible_datetime_accepts_full_iso8601():
    parsed = parse_flexible_datetime("2026-10-01T14:30:00+00:00")
    assert parsed.hour == 14


def test_parse_flexible_datetime_rejects_garbage_with_a_safe_message():
    with pytest.raises(ValueError, match="Could not parse 'not-a-date'"):
        parse_flexible_datetime("not-a-date")
