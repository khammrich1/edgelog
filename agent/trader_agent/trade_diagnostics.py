"""Pure helpers for the `trades` CLI diagnostic (issue #80 Step 2: the
real-account verification spike for /api/Trade/search).

Nothing here does network I/O, logging, or printing -- that keeps it
fully unit-testable with sanitized fixtures and keeps the redaction rules
in one reviewable place rather than scattered across cli.py/service.py.

This diagnostic exists because /api/Trade/search's response shape
(docs/integrations/projectx/PROJECTX_API_REFERENCE.md Sec.8) is
documented but, unlike Account/search and Contract/available, has never
been exercised against a live TopstepX account. summarize_trade_records
reports which documented fields a real response actually contains,
without ever surfacing the trader's real account/order/trade identifiers
or dollar figures -- only presence, observed type, and (for the two
small non-sensitive enums) the distinct raw values seen.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from trader_agent.providers.base import TradeRecord

# Field names exactly as documented in PROJECTX_API_REFERENCE.md Sec.8.
DOCUMENTED_TRADE_FIELDS = (
    "id",
    "accountId",
    "contractId",
    "creationTimestamp",
    "price",
    "profitAndLoss",
    "fees",
    "side",
    "size",
    "voided",
    "orderId",
)

# Identifies a specific account/order/trade/contract -- never print the
# value itself, only whether/how often it was present.
_IDENTIFIER_FIELDS = frozenset({"id", "accountId", "contractId", "orderId"})
# A dollar figure tied to the trader's real trading performance -- same
# redaction rule as the identifier fields.
_MONETARY_FIELDS = frozenset({"price", "profitAndLoss", "fees"})
# Small, non-sensitive enums. Showing the *distinct raw values* observed
# is the whole point of this spike (e.g. does `side` encode Buy/Sell as
# 0/1 or as a string?) and carries no financial information on its own.
_ENUM_FIELDS = frozenset({"side", "voided"})

COMMISSION_FEE_FINDING = (
    "/api/Trade/search's documented schema has exactly one cost field, "
    "`fees`, with no separate `commission` field and no documented split "
    "between exchange/clearing fees and other broker charges. EdgeLog's "
    "canonical model stores commission and fees as separate columns "
    "(migration 011). Unless a live response reveals an undocumented "
    "field (see unexpected_fields below), this endpoint alone cannot "
    "populate EdgeLog's `commission` column -- only one undifferentiated "
    "`fees` figure is available from trade history. /api/Order/search "
    "was not queried by this diagnostic and may or may not expose a "
    "different breakdown."
)


@dataclass(frozen=True)
class FieldObservation:
    field: str
    present_count: int
    observed_types: tuple[str, ...]
    distinct_values: Optional[tuple] = None  # populated only for _ENUM_FIELDS
    redacted: bool = False


@dataclass(frozen=True)
class TradeSearchReport:
    total_records: int
    field_observations: tuple[FieldObservation, ...]
    unexpected_fields: tuple[str, ...]
    commission_fee_finding: str


def summarize_trade_records(records: list[TradeRecord]) -> TradeSearchReport:
    """Reports, per documented field, how often it was present (non-null)
    across `records` and what Python type(s) its value took -- never the
    value itself for an identifier or monetary field. `records` should
    come straight from TopstepXRestClient.search_trades(); this function
    reads each record's raw dict so it sees exactly what the broker sent,
    not just what TradeRecord's own fixed fields happened to capture."""
    observations = []
    for field_name in DOCUMENTED_TRADE_FIELDS:
        present_values = [
            record.raw[field_name]
            for record in records
            if field_name in record.raw and record.raw[field_name] is not None
        ]
        observed_types = tuple(sorted({type(v).__name__ for v in present_values}))
        distinct_values = None
        if field_name in _ENUM_FIELDS and present_values:
            distinct_values = tuple(sorted({v for v in present_values}, key=str))
        observations.append(
            FieldObservation(
                field=field_name,
                present_count=len(present_values),
                observed_types=observed_types,
                distinct_values=distinct_values,
                redacted=field_name in _IDENTIFIER_FIELDS or field_name in _MONETARY_FIELDS,
            )
        )

    known = set(DOCUMENTED_TRADE_FIELDS)
    unexpected: set[str] = set()
    for record in records:
        unexpected.update(key for key in record.raw.keys() if key not in known)

    return TradeSearchReport(
        total_records=len(records),
        field_observations=tuple(observations),
        unexpected_fields=tuple(sorted(unexpected)),
        commission_fee_finding=COMMISSION_FEE_FINDING,
    )


def format_report(report: TradeSearchReport) -> str:
    """Renders a TradeSearchReport as plain text safe to paste into a
    GitHub issue/PR comment -- every line has already had sensitive
    values stripped by summarize_trade_records; this only formats what's
    left."""
    lines = [f"Retrieved {report.total_records} trade record(s)."]
    if report.total_records == 0:
        lines.append("No records in range -- field presence cannot be determined from an empty result.")

    lines.append("")
    lines.append(f"{'FIELD':<20}{'PRESENT':<14}{'TYPE(S)':<20}NOTES")
    for obs in report.field_observations:
        presence = f"{obs.present_count}/{report.total_records}"
        if obs.redacted:
            note = "(value redacted -- identifier/monetary field)"
        elif obs.distinct_values is not None:
            note = f"observed values: {obs.distinct_values}"
        else:
            note = ""
        lines.append(f"{obs.field:<20}{presence:<14}{(','.join(obs.observed_types) or '-'):<20}{note}")

    if report.unexpected_fields:
        lines.append("")
        lines.append("Fields present in the live response but NOT in the documented schema:")
        for name in report.unexpected_fields:
            flag = " (identifier-shaped name -- treat as sensitive, do not log elsewhere)" if "id" in name.lower() else ""
            lines.append(f"  - {name}{flag}")

    lines.append("")
    lines.append("Commission/fee finding:")
    lines.append(report.commission_fee_finding)
    return "\n".join(lines)


def redact_identifier(value: object) -> str:
    """Safe-to-log representation of an account/order/trade/contract
    identifier: never the real value, only enough to tell two log lines
    in the same run apart. Mirrors AgentConfig.masked_api_key's shape."""
    text = str(value)
    if len(text) <= 2:
        return "*" * len(text)
    return f"{'*' * (len(text) - 2)}{text[-2:]}"


def to_utc_iso(value: datetime) -> str:
    """Normalizes a (possibly naive) datetime to an ISO-8601 string in
    UTC -- naive values are assumed to already be UTC rather than the
    local machine's zone, since TopstepX's documented timestamps are
    ISO-8601 with no implied local offset."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def parse_flexible_datetime(text: str) -> datetime:
    """Accepts a bare date (YYYY-MM-DD, treated as UTC midnight) or a
    full ISO-8601 datetime, naive or with an offset. Raises ValueError
    with a message that is always safe to print to the user."""
    stripped = text.strip()
    try:
        if len(stripped) == 10:
            return datetime.strptime(stripped, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(stripped)
    except ValueError as exc:
        raise ValueError(f"Could not parse '{text}' as a date (YYYY-MM-DD) or ISO-8601 datetime") from exc
