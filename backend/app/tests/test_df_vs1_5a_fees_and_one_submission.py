"""DF-VS1.5a (issue #80): commission/fee capture, net P&L, one-submission
completed-trade entry, and the external-ID/account columns added as
groundwork for later import/sync slices (unused by any route in this
slice)."""
from decimal import Decimal

import pytest
from httpx import AsyncClient


async def _register_and_auth_headers(client: AsyncClient, email: str = "fees@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _open_day(client: AsyncClient, headers: dict, day: str = "2026-02-01"):
    await client.get(f"/api/v1/journal/days/{day}", headers=headers)
    return day


def _base_trade_payload(**overrides):
    payload = {
        "symbol": "MNQ",
        "direction": "long",
        "entry_price": "24500",
        "initial_quantity": 5,
        "entry_time": "2026-02-01T09:30:00Z",
        "setup": "Breakout",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_one_submission_completed_trade_creates_exit_atomically(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(
            exit_price="24600",
            exit_quantity=5,
            exit_time="2026-02-01T10:30:00Z",
            exit_commission="2.50",
            exit_fees="0.74",
        ),
    )
    assert create_resp.status_code == 201
    data = create_resp.json()

    assert data["status"] == "closed"
    assert len(data["exits"]) == 1
    exit_row = data["exits"][0]
    assert exit_row["quantity"] == 5
    assert Decimal(exit_row["exit_price"]) == Decimal("24600")
    assert Decimal(exit_row["commission"]) == Decimal("2.50")
    assert Decimal(exit_row["fees"]) == Decimal("0.74")
    # Long, entry 24500, exit 24600, qty 5, MNQ multiplier $2 -> 100pts*5*2=1000.
    assert Decimal(data["realized_pnl"]) == Decimal("1000")
    assert Decimal(data["net_pnl"]) == Decimal("996.76")  # 1000 - 2.50 - 0.74


@pytest.mark.asyncio
async def test_one_submission_rejects_partial_exit_fields(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(exit_price="24600"),  # missing exit_quantity/exit_time
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_one_submission_rejects_exit_quantity_over_initial_quantity(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(
            initial_quantity=5,
            exit_price="24600",
            exit_quantity=6,
            exit_time="2026-02-01T10:30:00Z",
        ),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_partial_one_submission_exit_leaves_trade_open(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(
            initial_quantity=5, exit_price="24600", exit_quantity=2, exit_time="2026-02-01T10:30:00Z"
        ),
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["status"] == "open"
    assert data["remaining_quantity"] == 3


@pytest.mark.asyncio
async def test_net_pnl_treats_unrecorded_cost_as_zero_not_unknown(client: AsyncClient):
    """No commission/fees entered anywhere -> net_pnl equals gross
    realized_pnl, not null -- the "no cost recorded yet" state is
    distinguishable from a confirmed zero only by the commission/fees
    fields themselves being null, not by net_pnl disappearing."""
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(
            exit_price="24600", exit_quantity=5, exit_time="2026-02-01T10:30:00Z"
        ),
    )
    data = create_resp.json()
    assert data["commission"] is None
    assert data["fees"] is None
    assert data["exits"][0]["commission"] is None
    assert Decimal(data["net_pnl"]) == Decimal(data["realized_pnl"]) == Decimal("1000")
    assert Decimal(data["total_commission"]) == Decimal("0")
    assert Decimal(data["total_fees"]) == Decimal("0")


@pytest.mark.asyncio
async def test_commission_and_fees_aggregate_across_entry_scale_in_and_exits(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(initial_quantity=2, commission="1.00", fees="0.30"),
    )
    trade_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/entries",
        headers=headers,
        json={
            "quantity": 2,
            "entry_price": "24520",
            "entry_time": "2026-02-01T09:35:00Z",
            "commission": "1.00",
            "fees": "0.30",
        },
    )
    exit_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={
            "quantity": 4,
            "exit_price": "24600",
            "exit_time": "2026-02-01T10:00:00Z",
            "commission": "2.00",
            "fees": "0.60",
        },
    )
    assert exit_resp.status_code == 201
    data = exit_resp.json()

    assert Decimal(data["total_commission"]) == Decimal("4.00")  # 1 + 1 + 2
    assert Decimal(data["total_fees"]) == Decimal("1.20")  # 0.3 + 0.3 + 0.6
    assert Decimal(data["net_pnl"]) == Decimal(data["realized_pnl"]) - Decimal("4.00") - Decimal("1.20")


@pytest.mark.asyncio
async def test_commission_editable_after_creation_via_update_trade(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    trade_id = create_resp.json()["id"]
    assert create_resp.json()["commission"] is None

    update_resp = await client.put(
        f"/api/v1/journal/days/{day}/trades/{trade_id}",
        headers=headers,
        json={"commission": "1.50", "fees": "0.40"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert Decimal(data["commission"]) == Decimal("1.50")
    assert Decimal(data["fees"]) == Decimal("0.40")


@pytest.mark.asyncio
async def test_exit_commission_editable_via_update_exit(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    trade_id = create_resp.json()["id"]
    exit_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 5, "exit_price": "24600", "exit_time": "2026-02-01T10:00:00Z"},
    )
    exit_id = exit_resp.json()["exits"][0]["id"]

    update_resp = await client.put(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits/{exit_id}",
        headers=headers,
        json={"commission": "3.00", "fees": "1.00"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert Decimal(data["exits"][0]["commission"]) == Decimal("3.00")
    assert Decimal(data["exits"][0]["fees"]) == Decimal("1.00")


@pytest.mark.asyncio
async def test_external_and_account_fields_are_null_and_unexposed_by_any_route(client: AsyncClient):
    """These columns exist for DF-VS1.5b/c groundwork only -- no route in
    this slice accepts or sets them, so every trade must read them back
    null, confirming nothing silently populates them."""
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    data = create_resp.json()
    assert data["external_trade_id"] is None
    assert data["external_order_id"] is None
    assert data["account_id"] is None
    assert data["account_label"] is None


@pytest.mark.asyncio
async def test_price_source_accepts_new_provenance_values(client: AsyncClient):
    """csv_import/api_sync are now valid price_source values even though no
    route sets them yet -- confirms the enum widening didn't break
    anything and is forward-compatible."""
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(price_source="csv_import"),
    )
    assert resp.status_code == 201
    assert resp.json()["price_source"] == "csv_import"


@pytest.mark.asyncio
async def test_existing_pre_migration_style_trade_reads_fine_with_null_fee_fields(client: AsyncClient):
    """A trade logged exactly like before this slice (no fee/one-submission
    fields at all) must load with every new field null, never a fabricated
    default -- same discipline as #78/#79's migrations."""
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["commission"] is None
    assert data["fees"] is None
    # No exit yet, but MNQ's multiplier is known, so realized_pnl/net_pnl
    # are 0 (truthfully nothing realized), not None -- None is reserved
    # for "multiplier unknown", a different kind of unknown.
    assert Decimal(data["realized_pnl"]) == Decimal("0")
    assert Decimal(data["net_pnl"]) == Decimal("0")
    assert data["exits"] == []
