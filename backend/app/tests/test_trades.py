"""Trade lifecycle endpoint tests (VS3)."""
from decimal import Decimal

import pytest
from httpx import AsyncClient


async def _register_and_auth_headers(client: AsyncClient, email: str = "trader@example.com") -> dict:
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
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_trades_require_auth(client: AsyncClient):
    response = await client.get("/api/v1/journal/days/2026-02-01/trades")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_long_trade(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    response = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )

    assert response.status_code == 201
    data = response.json()
    assert data["symbol"] == "MNQ"
    assert data["direction"] == "long"
    assert data["status"] == "open"
    assert data["remaining_quantity"] == 5
    assert data["exits"] == []


@pytest.mark.asyncio
async def test_create_short_trade(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    response = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(direction="short"),
    )

    assert response.status_code == 201
    assert response.json()["direction"] == "short"


@pytest.mark.asyncio
async def test_retrieve_trade(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    trade_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/journal/days/{day}/trades/{trade_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == trade_id


@pytest.mark.asyncio
async def test_update_trade(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    trade_id = create_response.json()["id"]

    response = await client.put(
        f"/api/v1/journal/days/{day}/trades/{trade_id}",
        headers=headers,
        json={"stop_price": "24480", "notes": "Broke out of the opening range", "setup": "ORB"},
    )

    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["stop_price"]) == Decimal("24480")
    assert data["notes"] == "Broke out of the opening range"
    assert data["setup"] == "ORB"


@pytest.mark.asyncio
async def test_delete_trade(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    trade_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/v1/journal/days/{day}/trades/{trade_id}", headers=headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/journal/days/{day}/trades/{trade_id}", headers=headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_add_partial_exit_updates_remaining_quantity(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    trade_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 2, "exit_price": "24510", "exit_time": "2026-02-01T09:45:00Z"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["remaining_quantity"] == 3
    assert data["status"] == "open"
    assert len(data["exits"]) == 1


@pytest.mark.asyncio
async def test_multiple_partial_exits(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    trade_id = create_response.json()["id"]

    await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 2, "exit_price": "24510", "exit_time": "2026-02-01T09:45:00Z"},
    )
    response = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 2, "exit_price": "24520", "exit_time": "2026-02-01T10:00:00Z"},
    )

    data = response.json()
    assert data["remaining_quantity"] == 1
    assert data["status"] == "open"
    assert len(data["exits"]) == 2


@pytest.mark.asyncio
async def test_final_exit_closes_trade(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    trade_id = create_response.json()["id"]

    await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 2, "exit_price": "24510", "exit_time": "2026-02-01T09:45:00Z"},
    )
    await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 2, "exit_price": "24520", "exit_time": "2026-02-01T10:00:00Z"},
    )
    response = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 1, "exit_price": "24530", "exit_time": "2026-02-01T10:15:00Z"},
    )

    data = response.json()
    assert data["remaining_quantity"] == 0
    assert data["status"] == "closed"


@pytest.mark.asyncio
async def test_reject_over_exit(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    trade_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 6, "exit_price": "24510", "exit_time": "2026-02-01T09:45:00Z"},
    )
    assert response.status_code == 400

    # Also reject once partially exited and the remainder is smaller than requested.
    await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 3, "exit_price": "24510", "exit_time": "2026-02-01T09:45:00Z"},
    )
    second_response = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 3, "exit_price": "24520", "exit_time": "2026-02-01T10:00:00Z"},
    )
    assert second_response.status_code == 400


@pytest.mark.asyncio
async def test_long_pnl_calculation(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(direction="long", entry_price="24500", initial_quantity=5),
    )
    trade_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 5, "exit_price": "24510", "exit_time": "2026-02-01T09:45:00Z"},
    )

    data = response.json()
    # (24510 - 24500) * 5 = 50 points; MNQ multiplier is $2/point -> $100.
    assert Decimal(data["realized_points"]) == Decimal("50")
    assert Decimal(data["realized_pnl"]) == Decimal("100")


@pytest.mark.asyncio
async def test_short_pnl_calculation(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(direction="short", entry_price="24500", initial_quantity=5),
    )
    trade_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 5, "exit_price": "24490", "exit_time": "2026-02-01T09:45:00Z"},
    )

    data = response.json()
    # (24500 - 24490) * 5 = 50 points; MNQ multiplier is $2/point -> $100.
    assert Decimal(data["realized_points"]) == Decimal("50")
    assert Decimal(data["realized_pnl"]) == Decimal("100")


@pytest.mark.asyncio
async def test_mnq_multiplier(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(symbol="MNQ", entry_price="100", initial_quantity=1),
    )
    trade_id = create_response.json()["id"]
    response = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 1, "exit_price": "101", "exit_time": "2026-02-01T09:45:00Z"},
    )
    assert Decimal(response.json()["realized_pnl"]) == Decimal("2")  # 1 point * $2


@pytest.mark.asyncio
async def test_mes_multiplier(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(symbol="MES", entry_price="100", initial_quantity=1),
    )
    trade_id = create_response.json()["id"]
    response = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 1, "exit_price": "101", "exit_time": "2026-02-01T09:45:00Z"},
    )
    assert Decimal(response.json()["realized_pnl"]) == Decimal("5")  # 1 point * $5


@pytest.mark.asyncio
async def test_mgc_multiplier(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(symbol="MGC", entry_price="100", initial_quantity=1),
    )
    trade_id = create_response.json()["id"]
    response = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 1, "exit_price": "101", "exit_time": "2026-02-01T09:45:00Z"},
    )
    assert Decimal(response.json()["realized_pnl"]) == Decimal("10")  # 1 point * $10


@pytest.mark.asyncio
async def test_mcl_multiplier(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(symbol="MCL", entry_price="100", initial_quantity=1),
    )
    trade_id = create_response.json()["id"]
    response = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 1, "exit_price": "101", "exit_time": "2026-02-01T09:45:00Z"},
    )
    assert Decimal(response.json()["realized_pnl"]) == Decimal("100")  # 1 point * $100


@pytest.mark.asyncio
async def test_planned_risk_calculation_long_and_short(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    long_response = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(
            direction="long", entry_price="24500", stop_price="24487.5", initial_quantity=1
        ),
    )
    long_data = long_response.json()
    assert Decimal(long_data["planned_risk_points"]) == Decimal("12.5")
    assert Decimal(long_data["planned_risk_dollars"]) == Decimal("25")  # 12.5 points * $2

    short_response = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(
            direction="short", entry_price="24500", stop_price="24512.5", initial_quantity=1
        ),
    )
    short_data = short_response.json()
    assert Decimal(short_data["planned_risk_points"]) == Decimal("12.5")
    assert Decimal(short_data["planned_risk_dollars"]) == Decimal("25")


@pytest.mark.asyncio
async def test_unknown_symbol_preserves_trade_without_guessing_dollars(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(symbol="ZZFAKE", entry_price="100", stop_price="95", initial_quantity=1),
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["multiplier_known"] is False
    assert Decimal(created["planned_risk_points"]) == Decimal("5")
    assert created["planned_risk_dollars"] is None

    trade_id = created["id"]
    exit_response = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 1, "exit_price": "110", "exit_time": "2026-02-01T09:45:00Z"},
    )
    exit_data = exit_response.json()
    assert Decimal(exit_data["realized_points"]) == Decimal("10")
    assert exit_data["realized_pnl"] is None


@pytest.mark.asyncio
async def test_user_isolation(client: AsyncClient):
    headers_a = await _register_and_auth_headers(client, email="trader-a@example.com")
    headers_b = await _register_and_auth_headers(client, email="trader-b@example.com")
    day = await _open_day(client, headers_a)
    await _open_day(client, headers_b)

    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers_a, json=_base_trade_payload()
    )
    trade_id = create_response.json()["id"]

    forbidden_get = await client.get(f"/api/v1/journal/days/{day}/trades/{trade_id}", headers=headers_b)
    assert forbidden_get.status_code == 404

    other_users_list = await client.get(f"/api/v1/journal/days/{day}/trades", headers=headers_b)
    assert other_users_list.json() == []


@pytest.mark.asyncio
async def test_locked_trading_day_prevents_trade_mutation_and_unlock_restores_it(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    trade_id = create_response.json()["id"]

    await client.post(f"/api/v1/journal/days/{day}/lock", headers=headers)

    blocked_create = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    assert blocked_create.status_code == 409

    blocked_update = await client.put(
        f"/api/v1/journal/days/{day}/trades/{trade_id}", headers=headers, json={"notes": "edit"}
    )
    assert blocked_update.status_code == 409

    blocked_exit = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 1, "exit_price": "24510", "exit_time": "2026-02-01T09:45:00Z"},
    )
    assert blocked_exit.status_code == 409

    await client.post(f"/api/v1/journal/days/{day}/unlock", headers=headers)

    allowed_update = await client.put(
        f"/api/v1/journal/days/{day}/trades/{trade_id}", headers=headers, json={"notes": "edit"}
    )
    assert allowed_update.status_code == 200


@pytest.mark.asyncio
async def test_invalid_quantity_rejected(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    response = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(initial_quantity=0),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_direction_rejected(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    response = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(direction="sideways"),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_prices_rejected(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)

    response = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json=_base_trade_payload(entry_price="0"),
    )
    assert response.status_code == 422

    create_response = await client.post(
        f"/api/v1/journal/days/{day}/trades", headers=headers, json=_base_trade_payload()
    )
    trade_id = create_response.json()["id"]
    exit_response = await client.post(
        f"/api/v1/journal/days/{day}/trades/{trade_id}/exits",
        headers=headers,
        json={"quantity": 1, "exit_price": "-5", "exit_time": "2026-02-01T09:45:00Z"},
    )
    assert exit_response.status_code == 422


@pytest.mark.asyncio
async def test_malformed_date_and_missing_trade_id(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    malformed_date = await client.get("/api/v1/journal/days/not-a-date/trades", headers=headers)
    assert malformed_date.status_code == 422

    day = await _open_day(client, headers)
    missing_trade = await client.get(f"/api/v1/journal/days/{day}/trades/999999", headers=headers)
    assert missing_trade.status_code == 404
