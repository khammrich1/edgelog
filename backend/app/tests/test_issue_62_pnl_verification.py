"""Issue #62 (P0): regression coverage for the exact scenarios the owner
reported as producing a wildly wrong realized P&L (-$19,884 instead of
+$116.00 gross).

Investigation finding: `_compute_trade_math` (backend/app/api/v1/trades.py),
the single source of truth for realized P&L, already produces the correct
figure for every scenario described in the issue -- verified here against
the exact entry/exit prices and quantities from the issue body, both via
direct unit calls to `_compute_trade_math` and end-to-end through the API.
The weighted-average-cost-basis logic and the per-point dollar multiplier
math have not changed since before this issue was filed (see trades.py's
git history). No production code change was made for this issue; these
tests exist to lock in the correct behavior permanently and to give a
concrete, reproducible basis for comparison if the discrepancy the owner
saw turns out to be a stale/cached render or a data-entry difference from
what was inferred off a screenshot, rather than a math bug.
"""
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.api.v1.trades import _compute_trade_math
from app.models.trades import Trade, TradeEntry, TradeExit


async def _register_and_auth_headers(client: AsyncClient, email: str = "pnl-verify@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _open_day(client: AsyncClient, headers: dict, day: str = "2026-02-01"):
    await client.get(f"/api/v1/journal/days/{day}", headers=headers)
    return day


def test_weighted_average_scenario_matches_issue_exactly():
    """The exact journal-side scenario from the issue: entry 1 @ 31224.25,
    scale-in 3 @ 31220 -> weighted average 31221.0625 (matches the issue's
    own stated "displayed average" exactly), exits 1 @ 31233, 2 @ 31235,
    1 @ 31239.25 -> gross +$116.00, not -$19,884."""
    trade = Trade(symbol="MNQ", direction="long", entry_price=Decimal("31224.25"), initial_quantity=1)
    entries = [TradeEntry(entry_price=Decimal("31220"), quantity=3)]
    exits = [
        TradeExit(exit_price=Decimal("31233"), quantity=1),
        TradeExit(exit_price=Decimal("31235"), quantity=2),
        TradeExit(exit_price=Decimal("31239.25"), quantity=1),
    ]

    result = _compute_trade_math(trade, exits, entries)

    assert result["average_entry_price"] == Decimal("31221.0625")
    assert result["realized_points"] == Decimal("58")
    assert result["realized_pnl"] == Decimal("116.00")
    assert result["status"] == "closed"
    assert result["remaining_quantity"] == 0


@pytest.mark.parametrize(
    "entry_price,quantity,exit_price,expected_gross",
    [
        ("31220.25", 1, "31239.25", "38.00"),  # broker row 1
        ("31220.25", 2, "31235.00", "59.00"),  # broker row 2
        ("31226.50", 1, "31233.00", "13.00"),  # broker row 3
        ("31175.00", 3, "31176.50", "9.00"),  # broker row 4 (distinct trade)
    ],
)
def test_each_broker_row_computes_correct_gross_independently(entry_price, quantity, exit_price, expected_gross):
    """The four owner-supplied TopstepX broker rows, each as its OWN
    independent trade (not merged) -- the issue explicitly warns the
    fourth row must never be auto-associated with the others. Confirms
    each row's gross P&L is correct standing alone."""
    trade = Trade(symbol="MNQ", direction="long", entry_price=Decimal(entry_price), initial_quantity=quantity)
    exits = [TradeExit(exit_price=Decimal(exit_price), quantity=quantity)]

    result = _compute_trade_math(trade, exits, [])

    assert result["realized_pnl"] == Decimal(expected_gross)


@pytest.mark.asyncio
async def test_four_broker_rows_as_separate_trades_never_combine(client: AsyncClient):
    """End-to-end: logging all four broker rows as four separate Trade
    records on the same day/symbol must never let one trade's figures leak
    into another's -- each must independently read back with its own
    correct gross P&L, and the day's total must be the simple sum (first
    three: $110.00; all four: $119.00), never some merged/averaged figure
    across trades that happen to share a symbol and day."""
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    broker_rows = [
        {"entry_price": "31220.25", "initial_quantity": 1, "exit_price": "31239.25", "exit_quantity": 1},
        {"entry_price": "31220.25", "initial_quantity": 2, "exit_price": "31235.00", "exit_quantity": 2},
        {"entry_price": "31226.50", "initial_quantity": 1, "exit_price": "31233.00", "exit_quantity": 1},
        {"entry_price": "31175.00", "initial_quantity": 3, "exit_price": "31176.50", "exit_quantity": 3},
    ]
    expected_gross = [Decimal("38.00"), Decimal("59.00"), Decimal("13.00"), Decimal("9.00")]

    created = []
    for i, row in enumerate(broker_rows):
        create_resp = await client.post(
            f"/api/v1/journal/days/{day}/trades",
            headers=headers,
            json={
                "symbol": "MNQZ26",
                "direction": "long",
                "entry_price": row["entry_price"],
                "initial_quantity": row["initial_quantity"],
                "entry_time": f"2026-02-01T{9 + i:02d}:30:00Z",
                "setup": "Broker reconciliation",
            },
        )
        assert create_resp.status_code == 201
        trade_id = create_resp.json()["id"]

        exit_resp = await client.post(
            f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
            headers=headers,
            json={
                "exit_price": row["exit_price"],
                "quantity": row["exit_quantity"],
                "exit_time": f"2026-02-01T{10 + i:02d}:00:00Z",
            },
        )
        assert exit_resp.status_code == 201
        created.append(exit_resp.json())

    for trade_data, expected in zip(created, expected_gross):
        assert Decimal(trade_data["realized_pnl"]) == expected, (
            f"trade {trade_data['id']} gross P&L leaked or miscalculated against a sibling trade"
        )

    list_resp = await client.get(f"/api/v1/journal/days/{day}/trades", headers=headers)
    all_trades = list_resp.json()
    assert len(all_trades) == 4
    total_gross = sum(Decimal(t["realized_pnl"]) for t in all_trades)
    assert total_gross == Decimal("119.00")
    first_three_gross = sum(Decimal(t["realized_pnl"]) for t in all_trades[:3])
    assert first_three_gross == Decimal("110.00")


@pytest.mark.asyncio
async def test_short_direction_weighted_average_sign_is_correct(client: AsyncClient):
    """Same weighted-average logic, short direction -- confirms the sign
    convention (profit when price falls) wasn't a contributor to the
    magnitude/sign error described in the issue."""
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json={
            "symbol": "MNQ",
            "direction": "short",
            "entry_price": "31224.25",
            "initial_quantity": 1,
            "entry_time": "2026-02-01T09:30:00Z",
            "setup": "Short verification",
        },
    )
    trade_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/entries",
        headers=headers,
        json={"entry_price": "31220", "quantity": 3, "entry_time": "2026-02-01T09:31:00Z"},
    )
    exit_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"exit_price": "31209.0625", "quantity": 4, "exit_time": "2026-02-01T10:00:00Z"},
    )
    data = exit_resp.json()
    assert data["average_entry_price"] == "31221.062500"
    # Short: profit = (avg_entry - exit) * qty = (31221.0625-31209.0625)*4 = 48 pts * $2 = $96.
    assert Decimal(data["realized_pnl"]) == Decimal("96.00")
