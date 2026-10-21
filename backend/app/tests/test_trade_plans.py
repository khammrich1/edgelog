"""Pre-trade plan endpoint tests (issue #59): Plan -> Review -> Approve/Reject."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade_plans import TradePlan
from app.models.trades import Trade, TradeEntry, TradeExit


async def _register_and_auth_headers(client: AsyncClient, email: str = "trader@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _iso_future(hours: int = 4) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


async def _register_broker_account(client: AsyncClient, headers: dict, **overrides) -> dict:
    payload = {"provider": "topstepx", "account_id": "PRACTICE-1", "label": "Practice 50K"}
    payload.update(overrides)
    response = await client.post("/api/v1/broker-accounts", headers=headers, json=payload)
    assert response.status_code == 201
    return response.json()


def _base_plan_payload(**overrides):
    payload = {
        "symbol": "MNQ",
        "direction": "long",
        "entry_price": "24500",
        "stop_price": "24480",
        "target_price": "24560",
        "quantity": 5,
        "setup": "Breakout",
        "expires_at": _iso_future(),
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_trade_plans_require_auth(client: AsyncClient):
    response = await client.get("/api/v1/trade-plans")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_long_plan_computes_risk_reward_with_mnq_multiplier(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    response = await client.post("/api/v1/trade-plans", headers=headers, json=_base_plan_payload())

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["revision_number"] == 1
    assert data["is_latest_revision"] is True
    assert data["multiplier_known"] is True
    # risk = (24500-24480) * 5 = 100 points; MNQ multiplier = 2 -> $200
    assert Decimal(data["risk_points"]) == Decimal("100")
    assert Decimal(data["risk_dollars"]) == Decimal("200.00")
    # reward = (24560-24500) * 5 = 300 points -> $600
    assert Decimal(data["reward_points"]) == Decimal("300")
    assert Decimal(data["reward_dollars"]) == Decimal("600.00")
    assert Decimal(data["reward_risk_ratio"]) == Decimal("3")


@pytest.mark.asyncio
async def test_create_short_plan_computes_risk_reward(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    response = await client.post(
        "/api/v1/trade-plans",
        headers=headers,
        json=_base_plan_payload(direction="short", entry_price="24500", stop_price="24520", target_price="24440"),
    )

    assert response.status_code == 201
    data = response.json()
    assert Decimal(data["risk_points"]) == Decimal("100")
    assert Decimal(data["reward_points"]) == Decimal("300")


@pytest.mark.asyncio
async def test_long_plan_rejects_stop_on_wrong_side(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    response = await client.post(
        "/api/v1/trade-plans",
        headers=headers,
        json=_base_plan_payload(stop_price="24510"),  # above entry on a long plan
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_long_plan_rejects_target_on_wrong_side(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    response = await client.post(
        "/api/v1/trade-plans",
        headers=headers,
        json=_base_plan_payload(target_price="24490"),  # below entry on a long plan
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_plan_rejects_expiry_in_the_past(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    response = await client.post(
        "/api/v1/trade-plans", headers=headers, json=_base_plan_payload(expires_at=past)
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unknown_symbol_plan_creates_but_blocks_approval(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    create_resp = await client.post(
        "/api/v1/trade-plans",
        headers=headers,
        json=_base_plan_payload(symbol="ZZZZ", target_price=None),
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["multiplier_known"] is False
    assert data["risk_dollars"] is None

    approve_resp = await client.post(f"/api/v1/trade-plans/{data['id']}/approve", headers=headers)
    assert approve_resp.status_code == 400
    assert "multiplier" in approve_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_approve_then_reapprove_conflicts(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    create_resp = await client.post("/api/v1/trade-plans", headers=headers, json=_base_plan_payload())
    plan_id = create_resp.json()["id"]

    approve_resp = await client.post(
        f"/api/v1/trade-plans/{plan_id}/approve", headers=headers, json={"decision_note": "Looks clean"}
    )
    assert approve_resp.status_code == 200
    data = approve_resp.json()
    assert data["status"] == "approved"
    assert data["decided_at"] is not None
    assert data["decision_note"] == "Looks clean"

    second_attempt = await client.post(f"/api/v1/trade-plans/{plan_id}/approve", headers=headers)
    assert second_attempt.status_code == 409


@pytest.mark.asyncio
async def test_reject_pending_plan(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    create_resp = await client.post("/api/v1/trade-plans", headers=headers, json=_base_plan_payload())
    plan_id = create_resp.json()["id"]

    reject_resp = await client.post(
        f"/api/v1/trade-plans/{plan_id}/reject", headers=headers, json={"decision_note": "No volume"}
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"

    again = await client.post(f"/api/v1/trade-plans/{plan_id}/reject", headers=headers)
    assert again.status_code == 409


@pytest.mark.asyncio
async def test_invalidate_pending_plan(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    create_resp = await client.post("/api/v1/trade-plans", headers=headers, json=_base_plan_payload())
    plan_id = create_resp.json()["id"]

    resp = await client.post(f"/api/v1/trade-plans/{plan_id}/invalidate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "invalidated"


@pytest.mark.asyncio
async def test_cancel_pending_and_approved_plans(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    pending_resp = await client.post("/api/v1/trade-plans", headers=headers, json=_base_plan_payload())
    pending_id = pending_resp.json()["id"]
    cancel_resp = await client.post(f"/api/v1/trade-plans/{pending_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "canceled"

    approved_resp = await client.post("/api/v1/trade-plans", headers=headers, json=_base_plan_payload())
    approved_id = approved_resp.json()["id"]
    await client.post(f"/api/v1/trade-plans/{approved_id}/approve", headers=headers)
    cancel_approved = await client.post(f"/api/v1/trade-plans/{approved_id}/cancel", headers=headers)
    assert cancel_approved.status_code == 200
    assert cancel_approved.json()["status"] == "canceled"

    # Already canceled -> conflict.
    again = await client.post(f"/api/v1/trade-plans/{pending_id}/cancel", headers=headers)
    assert again.status_code == 409


@pytest.mark.asyncio
async def test_expired_plan_fails_closed_on_approve(client: AsyncClient, db_session: AsyncSession):
    headers = await _register_and_auth_headers(client)
    create_resp = await client.post("/api/v1/trade-plans", headers=headers, json=_base_plan_payload())
    plan_id = create_resp.json()["id"]

    # Simulate the plan's validity window passing -- directly backdate
    # expires_at rather than waiting in real time.
    result = await db_session.execute(select(TradePlan).where(TradePlan.id == plan_id))
    plan = result.scalar_one()
    plan.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.flush()

    get_resp = await client.get(f"/api/v1/trade-plans/{plan_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "expired"

    approve_resp = await client.post(f"/api/v1/trade-plans/{plan_id}/approve", headers=headers)
    assert approve_resp.status_code == 409
    assert "expired" in approve_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_revise_creates_new_immutable_revision(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    create_resp = await client.post("/api/v1/trade-plans", headers=headers, json=_base_plan_payload())
    original = create_resp.json()
    original_id = original["id"]

    approve_resp = await client.post(
        f"/api/v1/trade-plans/{original_id}/approve", headers=headers, json={"decision_note": "go"}
    )
    assert approve_resp.json()["status"] == "approved"

    revise_resp = await client.post(
        f"/api/v1/trade-plans/{original_id}/revise",
        headers=headers,
        json=_base_plan_payload(quantity=10),
    )
    assert revise_resp.status_code == 201
    revised = revise_resp.json()
    assert revised["revision_number"] == 2
    assert revised["previous_version_id"] == original_id
    assert revised["status"] == "pending"
    assert revised["quantity"] == 10

    # The original's own decision is untouched -- immutability of the
    # approved snapshot.
    original_after = await client.get(f"/api/v1/trade-plans/{original_id}", headers=headers)
    original_after_data = original_after.json()
    assert original_after_data["status"] == "approved"
    assert original_after_data["decision_note"] == "go"
    assert original_after_data["is_latest_revision"] is False

    # Revising the now-superseded original again is rejected.
    again = await client.post(
        f"/api/v1/trade-plans/{original_id}/revise", headers=headers, json=_base_plan_payload()
    )
    assert again.status_code == 409

    # The default list only shows the latest revision in the chain.
    list_resp = await client.get("/api/v1/trade-plans", headers=headers)
    ids = [p["id"] for p in list_resp.json()]
    assert revised["id"] in ids
    assert original_id not in ids

    list_all_resp = await client.get("/api/v1/trade-plans?include_superseded=true", headers=headers)
    all_ids = [p["id"] for p in list_all_resp.json()]
    assert original_id in all_ids
    assert revised["id"] in all_ids


@pytest.mark.asyncio
async def test_plan_can_link_an_owned_broker_account(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    account = await _register_broker_account(client, headers)

    response = await client.post(
        "/api/v1/trade-plans", headers=headers, json=_base_plan_payload(broker_account_id=account["id"])
    )

    assert response.status_code == 201
    data = response.json()
    assert data["broker_account_id"] == account["id"]
    assert data["broker_account_label"] == "Practice 50K"
    assert data["broker_account_provider"] == "topstepx"
    assert data["broker_account_account_id"] == "PRACTICE-1"


@pytest.mark.asyncio
async def test_plan_rejects_another_users_broker_account(client: AsyncClient):
    headers_a = await _register_and_auth_headers(client, email="a@example.com")
    headers_b = await _register_and_auth_headers(client, email="b@example.com")
    account_b = await _register_broker_account(client, headers_b)

    response = await client.post(
        "/api/v1/trade-plans", headers=headers_a, json=_base_plan_payload(broker_account_id=account_b["id"])
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_plans_are_isolated_per_user(client: AsyncClient):
    headers_a = await _register_and_auth_headers(client, email="a@example.com")
    headers_b = await _register_and_auth_headers(client, email="b@example.com")

    create_resp = await client.post("/api/v1/trade-plans", headers=headers_a, json=_base_plan_payload())
    plan_id = create_resp.json()["id"]

    get_as_b = await client.get(f"/api/v1/trade-plans/{plan_id}", headers=headers_b)
    assert get_as_b.status_code == 404

    approve_as_b = await client.post(f"/api/v1/trade-plans/{plan_id}/approve", headers=headers_b)
    assert approve_as_b.status_code == 404

    list_as_b = await client.get("/api/v1/trade-plans", headers=headers_b)
    assert list_as_b.json() == []


@pytest.mark.asyncio
async def test_max_risk_dollars_exceeded_flag(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.post(
        "/api/v1/trade-plans",
        headers=headers,
        json=_base_plan_payload(max_risk_dollars="50"),  # actual risk is $200
    )
    data = response.json()
    assert data["exceeds_max_risk"] is True


@pytest.mark.asyncio
async def test_plan_lifecycle_never_creates_trade_rows(client: AsyncClient, db_session: AsyncSession):
    headers = await _register_and_auth_headers(client)
    create_resp = await client.post("/api/v1/trade-plans", headers=headers, json=_base_plan_payload())
    plan_id = create_resp.json()["id"]
    await client.post(f"/api/v1/trade-plans/{plan_id}/approve", headers=headers)
    await client.post(
        f"/api/v1/trade-plans/{plan_id}/revise", headers=headers, json=_base_plan_payload(quantity=1)
    )

    trade_count = await db_session.scalar(select(func.count()).select_from(Trade))
    entry_count = await db_session.scalar(select(func.count()).select_from(TradeEntry))
    exit_count = await db_session.scalar(select(func.count()).select_from(TradeExit))
    assert trade_count == 0
    assert entry_count == 0
    assert exit_count == 0


@pytest.mark.asyncio
async def test_plan_persists_across_requests(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    create_resp = await client.post("/api/v1/trade-plans", headers=headers, json=_base_plan_payload())
    plan_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/trade-plans/{plan_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == plan_id

    list_resp = await client.get("/api/v1/trade-plans", headers=headers)
    assert any(p["id"] == plan_id for p in list_resp.json())
