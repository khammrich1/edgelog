"""Trade Calendar range-query endpoint tests (VS4)."""
from decimal import Decimal

import pytest
from httpx import AsyncClient


async def _register_and_auth_headers(client: AsyncClient, email: str = "calendar@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _open_day(client: AsyncClient, headers: dict, day: str) -> str:
    await client.get(f"/api/v1/journal/days/{day}", headers=headers)
    return day


def _base_trade_payload(**overrides):
    payload = {
        "symbol": "MNQ",
        "direction": "long",
        "entry_price": "24500",
        "initial_quantity": 5,
        "entry_time": "2026-02-02T09:30:00Z",
    }
    payload.update(overrides)
    return payload


async def _create_trade(client: AsyncClient, headers: dict, day: str, **overrides) -> dict:
    response = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(**overrides),
    )
    return response.json()


@pytest.mark.asyncio
async def test_calendar_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/journal/trades", params={"start": "2026-02-02", "end": "2026-02-08"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_calendar_end_before_start_returns_400(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.get(
        "/api/v1/journal/trades", headers=headers, params={"start": "2026-02-08", "end": "2026-02-02"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "end must not be before start"


@pytest.mark.asyncio
async def test_calendar_malformed_date_returns_422(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.get(
        "/api/v1/journal/trades", headers=headers, params={"start": "not-a-date", "end": "2026-02-08"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_calendar_empty_range_returns_empty_list(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.get(
        "/api/v1/journal/trades", headers=headers, params={"start": "2026-02-02", "end": "2026-02-08"}
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_calendar_groups_trades_by_day(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    monday = await _open_day(client, headers, "2026-02-02")
    wednesday = await _open_day(client, headers, "2026-02-04")

    await _create_trade(client, headers, monday, entry_time="2026-02-02T09:30:00Z")
    await _create_trade(client, headers, wednesday, symbol="MES", entry_time="2026-02-04T09:30:00Z")

    response = await client.get(
        "/api/v1/journal/trades", headers=headers, params={"start": "2026-02-02", "end": "2026-02-08"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    by_date = {day["date"]: day for day in data}
    assert by_date["2026-02-02"]["trades"][0]["symbol"] == "MNQ"
    assert by_date["2026-02-04"]["trades"][0]["symbol"] == "MES"


@pytest.mark.asyncio
async def test_calendar_multiple_trades_same_day_ordered_by_entry_time(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers, "2026-02-02")

    await _create_trade(client, headers, day, symbol="MES", entry_time="2026-02-02T14:00:00Z")
    await _create_trade(client, headers, day, symbol="MNQ", entry_time="2026-02-02T09:00:00Z")

    response = await client.get(
        "/api/v1/journal/trades", headers=headers, params={"start": "2026-02-02", "end": "2026-02-02"}
    )
    data = response.json()
    assert len(data) == 1
    trades = data[0]["trades"]
    assert len(trades) == 2
    assert [t["symbol"] for t in trades] == ["MNQ", "MES"]


@pytest.mark.asyncio
async def test_calendar_excludes_trades_outside_range(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    before = await _open_day(client, headers, "2026-02-01")
    inside = await _open_day(client, headers, "2026-02-02")
    after = await _open_day(client, headers, "2026-02-09")

    await _create_trade(client, headers, before, entry_time="2026-02-01T09:30:00Z")
    await _create_trade(client, headers, inside, entry_time="2026-02-02T09:30:00Z")
    await _create_trade(client, headers, after, entry_time="2026-02-09T09:30:00Z")

    response = await client.get(
        "/api/v1/journal/trades", headers=headers, params={"start": "2026-02-02", "end": "2026-02-08"}
    )
    data = response.json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-02-02"


@pytest.mark.asyncio
async def test_calendar_user_isolation(client: AsyncClient):
    headers_a = await _register_and_auth_headers(client, email="calendar_a@example.com")
    headers_b = await _register_and_auth_headers(client, email="calendar_b@example.com")
    day = await _open_day(client, headers_a, "2026-02-02")
    await _create_trade(client, headers_a, day)

    response = await client.get(
        "/api/v1/journal/trades", headers=headers_b, params={"start": "2026-02-02", "end": "2026-02-08"}
    )
    assert response.json() == []


@pytest.mark.asyncio
async def test_calendar_includes_open_closed_and_canceled_statuses(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers, "2026-02-02")

    open_trade = await _create_trade(client, headers, day, entry_time="2026-02-02T09:00:00Z")

    closed_trade = await _create_trade(client, headers, day, entry_time="2026-02-02T10:00:00Z")
    await client.post(
        f"/api/v1/journal/days/{day}/trades/{closed_trade['id']}/exits",
        headers=headers,
        json={"quantity": 5, "exit_price": "24600", "exit_time": "2026-02-02T11:00:00Z"},
    )

    canceled_trade = await _create_trade(client, headers, day, entry_time="2026-02-02T12:00:00Z")
    await client.post(f"/api/v1/journal/days/{day}/trades/{canceled_trade['id']}/cancel", headers=headers)

    response = await client.get(
        "/api/v1/journal/trades", headers=headers, params={"start": "2026-02-02", "end": "2026-02-02"}
    )
    data = response.json()
    statuses = {t["id"]: t["status"] for t in data[0]["trades"]}
    assert statuses[open_trade["id"]] == "open"
    assert statuses[closed_trade["id"]] == "closed"
    assert statuses[canceled_trade["id"]] == "canceled"


@pytest.mark.asyncio
async def test_calendar_math_matches_single_day_endpoint_with_scale_in_and_trim(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers, "2026-02-02")
    trade = await _create_trade(client, headers, day, entry_time="2026-02-02T09:00:00Z")

    await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade['id']}/entries",
        headers=headers,
        json={"quantity": 5, "entry_price": "24600", "entry_time": "2026-02-02T09:15:00Z"},
    )
    await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade['id']}/exits",
        headers=headers,
        json={"quantity": 4, "exit_price": "24700", "exit_time": "2026-02-02T10:00:00Z"},
    )

    single_day_response = await client.get(f"/api/v1/journal/days/{day}/trades", headers=headers)
    single_day_trade = next(t for t in single_day_response.json() if t["id"] == trade["id"])

    range_response = await client.get(
        "/api/v1/journal/trades", headers=headers, params={"start": "2026-02-02", "end": "2026-02-02"}
    )
    range_trade = range_response.json()[0]["trades"][0]

    assert single_day_trade["status"] == range_trade["status"]
    for field in (
        "realized_pnl",
        "average_entry_price",
        "remaining_quantity",
        "total_quantity",
        "realized_points",
    ):
        assert Decimal(str(single_day_trade[field])) == Decimal(str(range_trade[field])), field


@pytest.mark.asyncio
async def test_calendar_does_not_create_trading_day_rows(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    response = await client.get(
        "/api/v1/journal/trades", headers=headers, params={"start": "2026-02-02", "end": "2026-02-08"}
    )
    assert response.status_code == 200

    # A never-opened day still 404s for the single-day trades endpoint --
    # confirms the range query above didn't vivify a TradingDay row for it.
    single_day_response = await client.get("/api/v1/journal/days/2026-02-05/trades", headers=headers)
    assert single_day_response.status_code == 404
