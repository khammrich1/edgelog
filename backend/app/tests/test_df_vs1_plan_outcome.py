"""DF-VS1 (issue #78): plan-vs-outcome evidence capture on the existing,
single canonical Trade/TradingDay rows -- no parallel trade lifecycle."""
from datetime import date as date_type

import pytest
from httpx import AsyncClient


async def _register_and_auth_headers(client: AsyncClient, email: str = "planner@example.com") -> dict:
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
async def test_plan_snapshot_immutable_after_stop_moved(client: AsyncClient):
    """The core ask: moving the live stop (e.g. to breakeven) must not
    rewrite what the original plan was, and risk/R displays must not
    misrepresent the moved stop as the original planned risk."""
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(
            stop_price="24450",
            target_price="24600",
            planned_stop_price="24450",
            planned_target_price="24600",
            plan_rationale="Breakout retest with volume confirmation.",
            plan_verified=True,
        ),
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    trade_id = created["id"]
    assert created["planned_stop_price"] == "24450.000000"
    assert created["planned_quantity"] == 5
    assert created["plan_verified_at"] is not None
    # Long, entry 24500, planned stop 24450, qty 5 -> 50pts * 5 = 250.
    assert created["original_planned_risk_points"] == "250.000000"

    # Trader moves the stop to breakeven after entry -- a legitimate,
    # common action that must NOT touch the plan snapshot.
    update_resp = await client.put(
        f"/api/v1/journal/days/{day}/trades/{trade_id}",
        headers=headers,
        json={"stop_price": "24500"},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()

    assert updated["stop_price"] == "24500.000000"
    assert updated["planned_stop_price"] == "24450.000000", "plan snapshot must survive a live stop edit"
    assert updated["planned_target_price"] == "24600.000000"
    assert updated["plan_rationale"] == "Breakout retest with volume confirmation."

    # Current-stop risk recalculates (now zero risk at breakeven); the
    # original-plan risk must stay exactly what it was at entry.
    assert updated["planned_risk_points"] == "0.000000"
    assert updated["original_planned_risk_points"] == "250.000000"


@pytest.mark.asyncio
async def test_trade_update_schema_cannot_edit_plan_fields(client: AsyncClient):
    """TradeUpdate has no planned_* fields at all -- even sending them
    should have zero effect, never silently coerced or accepted."""
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(planned_stop_price="24450", plan_verified=True),
    )
    trade_id = create_resp.json()["id"]

    # Extra/unknown fields in the PUT body are simply ignored by pydantic.
    update_resp = await client.put(
        f"/api/v1/journal/days/{day}/trades/{trade_id}",
        headers=headers,
        json={"planned_stop_price": "1", "plan_verified_at": "2020-01-01T00:00:00Z"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["planned_stop_price"] == "24450.000000"
    assert data["plan_verified_at"] is not None
    assert not data["plan_verified_at"].startswith("2020")


@pytest.mark.asyncio
async def test_partial_exit_does_not_affect_plan_snapshot(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(stop_price="24450", planned_stop_price="24450", plan_verified=True),
    )
    trade_id = create_resp.json()["id"]

    exit_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 2, "exit_price": "24550", "exit_time": "2026-02-01T10:00:00Z"},
    )
    assert exit_resp.status_code == 201
    data = exit_resp.json()

    assert data["status"] == "open"
    assert data["remaining_quantity"] == 3
    assert data["planned_stop_price"] == "24450.000000"
    assert data["planned_quantity"] == 5, "plan snapshot reflects the original full size, not what remains"
    assert data["original_planned_risk_points"] == "250.000000"


@pytest.mark.asyncio
async def test_trade_with_no_plan_recorded_has_null_plan_fields(client: AsyncClient):
    """A trade logged with no planned_* at all -- e.g. a historical trade
    predating this slice, or a trader who just didn't fill in the plan --
    must read back with everything null, never a fabricated default."""
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    assert create_resp.status_code == 201
    data = create_resp.json()

    assert data["planned_stop_price"] is None
    assert data["planned_target_price"] is None
    assert data["plan_rationale"] is None
    assert data["plan_verified_at"] is None
    assert data["original_planned_risk_points"] is None
    assert data["original_planned_risk_dollars"] is None
    assert data["rule_adherence"] is None
    assert data["rule_adherence_note"] is None
    assert data["reflection_notes"] is None
    # planned_quantity is still always snapshotted, independent of whether
    # a stop/target plan was recorded -- it's free, derived from a field
    # that's already required on every trade.
    assert data["planned_quantity"] == 5


@pytest.mark.asyncio
async def test_retrospective_entry_never_labeled_verified_pretrade(client: AsyncClient):
    """Filling in plan fields without asserting plan_verified must leave
    plan_verified_at null -- a retrospective entry can look exactly like a
    verified one in its stop/target/rationale, but must never be labeled
    pre-trade-verified evidence just because the fields are populated."""
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(
            planned_stop_price="24450",
            planned_target_price="24600",
            plan_rationale="Entered retrospectively from memory after the session.",
            plan_verified=False,
        ),
    )
    assert create_resp.status_code == 201
    data = create_resp.json()

    assert data["planned_stop_price"] == "24450.000000"
    assert data["plan_rationale"] is not None
    assert data["plan_verified_at"] is None, "unverified plan fields must never imply pre-trade evidence"


@pytest.mark.asyncio
async def test_per_trade_rule_adherence_and_reflection_persist(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    trade_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/journal/days/{day}/trades/{trade_id}",
        headers=headers,
        json={
            "rule_adherence": "no",
            "rule_adherence_note": "Sized up after a loss, against plan.",
            "reflection_notes": "Should have walked away after the first stop-out.",
        },
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["rule_adherence"] == "no"
    assert data["rule_adherence_note"] == "Sized up after a loss, against plan."
    assert data["reflection_notes"] == "Should have walked away after the first stop-out."

    # Persists across a fresh read, not just the mutating response.
    get_resp = await client.get(f"/api/v1/journal/days/{day}/trades/{trade_id}", headers=headers)
    assert get_resp.json()["rule_adherence"] == "no"

    # A later unrelated edit must not clear or reset the outcome fields.
    second_update = await client.put(
        f"/api/v1/journal/days/{day}/trades/{trade_id}",
        headers=headers,
        json={"notes": "unrelated note change"},
    )
    assert second_update.json()["rule_adherence"] == "no"
    assert second_update.json()["reflection_notes"] == "Should have walked away after the first stop-out."


@pytest.mark.asyncio
async def test_rule_adherence_rejects_invalid_value(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    trade_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/journal/days/{day}/trades/{trade_id}",
        headers=headers,
        json={"rule_adherence": "maybe"},
    )
    assert update_resp.status_code == 422


@pytest.mark.asyncio
async def test_trading_day_intended_to_trade_and_eod_reflection_persist(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = "2026-02-02"
    await client.get(f"/api/v1/journal/days/{day}", headers=headers)

    update_resp = await client.put(
        f"/api/v1/journal/days/{day}",
        headers=headers,
        json={"intended_to_trade": False, "eod_reflection": "No-trade day: no A+ setups formed."},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["intended_to_trade"] is False
    assert data["eod_reflection"] == "No-trade day: no A+ setups formed."

    get_resp = await client.get(f"/api/v1/journal/days/{day}", headers=headers)
    data = get_resp.json()
    assert data["intended_to_trade"] is False
    assert data["eod_reflection"] == "No-trade day: no A+ setups formed."


@pytest.mark.asyncio
async def test_trading_day_without_intended_to_trade_set_is_null_not_fabricated(client: AsyncClient):
    """A day nobody has marked either way (including every pre-existing
    historical day) must read back null, not default to true or false."""
    headers = await _register_and_auth_headers(client)
    day = "2026-02-03"

    get_resp = await client.get(f"/api/v1/journal/days/{day}", headers=headers)
    data = get_resp.json()
    assert data["intended_to_trade"] is None
    assert data["eod_reflection"] is None
