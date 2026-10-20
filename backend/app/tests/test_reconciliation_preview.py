"""API-level tests for POST /api/v1/journal/reconciliation/preview
(issue #80 Step 3A). Covers what the pure-logic tests in
test_reconciliation_service.py don't: auth, request validation, the
account-scope guard, and -- the one thing that matters most for an
endpoint explicitly promised to make zero writes -- that the database is
provably unchanged before and after a call, even one that matches an
existing plan."""
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trades import Trade, TradeEntry, TradeExit

PREVIEW_URL = "/api/v1/journal/reconciliation/preview"


async def _register_and_auth_headers(client: AsyncClient, email: str = "reconcile@example.com") -> dict:
    response = await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _open_day(client: AsyncClient, headers: dict, day: str = "2026-10-16"):
    await client.get(f"/api/v1/journal/days/{day}", headers=headers)
    return day


def _execution(**overrides):
    payload = {
        "id": 1001,
        "accountId": 28592949,
        "contractId": "CON.F.US.MNQ.Z25",
        "creationTimestamp": "2026-10-16T14:30:00Z",
        "price": "21000",
        "size": 2,
        "side": 0,
        "orderId": 500,
        "fees": "2.50",
        "commissions": "0.62",
        "voided": False,
    }
    payload.update(overrides)
    return payload


async def _row_counts(db_session: AsyncSession) -> tuple[int, int, int]:
    trades = (await db_session.execute(select(func.count()).select_from(Trade))).scalar_one()
    entries = (await db_session.execute(select(func.count()).select_from(TradeEntry))).scalar_one()
    exits = (await db_session.execute(select(func.count()).select_from(TradeExit))).scalar_one()
    return trades, entries, exits


@pytest.mark.asyncio
async def test_preview_requires_authentication(client: AsyncClient):
    response = await client.post(
        PREVIEW_URL,
        json={"account_id": 1, "date": "2026-10-16", "executions": [_execution()]},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_preview_rejects_malformed_execution_batch(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    bad_execution = _execution()
    del bad_execution["price"]  # required field missing

    response = await client.post(
        PREVIEW_URL,
        headers=headers,
        json={"account_id": 28592949, "date": "2026-10-16", "executions": [bad_execution]},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_preview_rejects_an_empty_execution_batch(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    response = await client.post(
        PREVIEW_URL,
        headers=headers,
        json={"account_id": 28592949, "date": "2026-10-16", "executions": []},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_preview_rejects_execution_from_a_different_account(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    response = await client.post(
        PREVIEW_URL,
        headers=headers,
        json={
            "account_id": 28592949,
            "date": "2026-10-16",
            "executions": [_execution(accountId=99999999)],
        },
    )
    assert response.status_code == 400
    assert "1001" in response.json()["detail"]


@pytest.mark.asyncio
async def test_preview_makes_zero_database_writes(client: AsyncClient, db_session: AsyncSession):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json={
            "symbol": "MNQ",
            "direction": "long",
            "entry_price": "21000",
            "initial_quantity": 2,
            "entry_time": "2026-10-16T09:30:00Z",
            "setup": "Breakout",
        },
    )

    before = await _row_counts(db_session)

    response = await client.post(
        PREVIEW_URL,
        headers=headers,
        json={
            "account_id": 28592949,
            "date": "2026-10-16",
            "executions": [
                _execution(id=1, orderId=1, price="21000", creationTimestamp="2026-10-16T09:30:00Z"),
                _execution(id=2, orderId=1, price="21050", creationTimestamp="2026-10-16T10:00:00Z"),
            ],
        },
    )
    assert response.status_code == 200

    after = await _row_counts(db_session)
    assert before == after


@pytest.mark.asyncio
async def test_preview_proposes_a_candidate_match_against_an_existing_plan(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json={
            "symbol": "MNQ",
            "direction": "long",
            "entry_price": "21000",
            "initial_quantity": 2,
            "entry_time": "2026-10-16T09:30:00Z",
            "setup": "Breakout",
        },
    )
    trade_id = create_resp.json()["id"]

    response = await client.post(
        PREVIEW_URL,
        headers=headers,
        json={
            "account_id": 28592949,
            "date": "2026-10-16",
            "executions": [
                _execution(id=1, orderId=1, side=0, price="21000", creationTimestamp="2026-10-16T09:30:00Z"),
                _execution(id=2, orderId=1, side=1, price="21050", creationTimestamp="2026-10-16T10:00:00Z"),
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()

    assert body["summary"]["total_executions"] == 2
    assert body["summary"]["candidate_plan_matches"] == 1
    assert body["summary"]["groups_with_candidate_pnl"] == 1

    group = next(g for g in body["fill_groups"] if 1 in g["execution_ids"])
    assert group["plan_match_status"] == "candidate_match"
    assert group["candidate_trade_ids"] == [trade_id]
    assert group["pnl_status"] == "candidate"
    assert Decimal(group["candidate_gross_pnl"]) == Decimal("200")  # 50pts * 2 * $2 MNQ multiplier


@pytest.mark.asyncio
async def test_preview_marks_unplanned_execution_when_no_plan_exists(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    await _open_day(client, headers)

    response = await client.post(
        PREVIEW_URL,
        headers=headers,
        json={
            "account_id": 28592949,
            "date": "2026-10-16",
            "executions": [
                _execution(id=1, orderId=1, creationTimestamp="2026-10-16T09:30:00Z"),
                _execution(id=2, orderId=1, creationTimestamp="2026-10-16T10:00:00Z"),
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["unplanned_groups"] == 1

    group = body["fill_groups"][0]
    assert group["plan_match_status"] == "unplanned"
    assert "Unplanned" in group["plan_match_note"] or "unplanned" in group["plan_match_note"].lower()


@pytest.mark.asyncio
async def test_preview_surfaces_fees_and_commissions_without_combining_them(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    await _open_day(client, headers)

    response = await client.post(
        PREVIEW_URL,
        headers=headers,
        json={
            "account_id": 28592949,
            "date": "2026-10-16",
            "executions": [_execution(id=1, fees="2.50", commissions="0.62")],
        },
    )
    assert response.status_code == 200
    execution = response.json()["executions"][0]
    assert Decimal(execution["fees"]) == Decimal("2.50")
    assert Decimal(execution["commissions"]) == Decimal("0.62")


@pytest.mark.asyncio
async def test_preview_flags_a_voided_execution(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    await _open_day(client, headers)

    response = await client.post(
        PREVIEW_URL,
        headers=headers,
        json={
            "account_id": 28592949,
            "date": "2026-10-16",
            "executions": [_execution(id=1, voided=True)],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["voided_count"] == 1
    assert body["fill_groups"][0]["voided"] is True
    assert body["fill_groups"][0]["pnl_status"] == "unresolved"


@pytest.mark.asyncio
async def test_preview_detects_a_duplicate_already_imported_execution(client: AsyncClient, db_session: AsyncSession):
    headers = await _register_and_auth_headers(client)
    day = await _open_day(client, headers)
    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json={
            "symbol": "MNQ",
            "direction": "long",
            "entry_price": "21000",
            "initial_quantity": 2,
            "entry_time": "2026-10-16T09:30:00Z",
            "setup": "Breakout",
        },
    )
    trade_id = create_resp.json()["id"]

    # Simulate a prior reconciliation import having already claimed this
    # execution's broker order ID -- no import endpoint exists yet in
    # this slice, and update_trade deliberately doesn't expose external_*
    # fields, so the fixture sets it directly on the same session the app
    # itself uses (the `client` fixture overrides get_db with db_session).
    trade = (await db_session.execute(select(Trade).where(Trade.id == trade_id))).scalar_one()
    trade.external_order_id = "500"
    await db_session.flush()

    response = await client.post(
        PREVIEW_URL,
        headers=headers,
        json={
            "account_id": 28592949,
            "date": "2026-10-16",
            "executions": [
                _execution(id=1, orderId=500, creationTimestamp="2026-10-16T09:30:00Z"),
                _execution(id=2, orderId=500, creationTimestamp="2026-10-16T09:31:00Z"),
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["already_imported_count"] == 2

    execution = next(e for e in body["executions"] if e["id"] == 1)
    assert execution["already_imported"] is True
    assert execution["already_imported_trade_id"] == trade_id


@pytest.mark.asyncio
async def test_preview_cannot_surface_another_users_trade_as_already_imported(client: AsyncClient, db_session: AsyncSession):
    """User A's Trade carries external_order_id=500. User B previews a
    batch with an execution reporting that same orderId, on the same
    date. User B must never see User A's trade -- not as a duplicate,
    not as anything -- because candidate-trade loading is scoped by
    user_id, independent of what account_id or orderId is claimed."""
    headers_a = await _register_and_auth_headers(client, email="user-a@example.com")
    day = await _open_day(client, headers_a)
    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers_a,
        json={
            "symbol": "MNQ",
            "direction": "long",
            "entry_price": "21000",
            "initial_quantity": 2,
            "entry_time": "2026-10-16T09:30:00Z",
            "setup": "Breakout",
        },
    )
    trade_id_a = create_resp.json()["id"]
    trade_a = (await db_session.execute(select(Trade).where(Trade.id == trade_id_a))).scalar_one()
    trade_a.external_order_id = "500"
    await db_session.flush()

    headers_b = await _register_and_auth_headers(client, email="user-b@example.com")
    await _open_day(client, headers_b)

    response = await client.post(
        PREVIEW_URL,
        headers=headers_b,
        json={
            "account_id": 28592949,
            "date": "2026-10-16",
            "executions": [
                _execution(id=1, orderId=500, creationTimestamp="2026-10-16T09:30:00Z"),
                _execution(id=2, orderId=500, creationTimestamp="2026-10-16T09:31:00Z"),
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()

    assert body["summary"]["already_imported_count"] == 0
    execution = next(e for e in body["executions"] if e["id"] == 1)
    assert execution["already_imported"] is False
    assert execution["already_imported_trade_id"] is None
    # Not matched against A's trade, and not A's trade_id anywhere in the response.
    assert trade_id_a not in [tid for g in body["fill_groups"] for tid in g["candidate_trade_ids"]]


@pytest.mark.asyncio
async def test_preview_cannot_propose_another_users_trade_as_a_candidate_match(client: AsyncClient):
    """User A has a planned MNQ trade on 2026-10-16. User B, previewing
    their own executions for the identical symbol/date, must never see
    User A's trade proposed as a candidate -- it must come back
    unplanned, since User B genuinely has no matching plan of their own."""
    headers_a = await _register_and_auth_headers(client, email="user-a2@example.com")
    day = await _open_day(client, headers_a)
    await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers_a,
        json={
            "symbol": "MNQ",
            "direction": "long",
            "entry_price": "21000",
            "initial_quantity": 2,
            "entry_time": "2026-10-16T09:30:00Z",
            "setup": "Breakout",
        },
    )

    headers_b = await _register_and_auth_headers(client, email="user-b2@example.com")
    await _open_day(client, headers_b)

    response = await client.post(
        PREVIEW_URL,
        headers=headers_b,
        json={
            "account_id": 28592949,
            "date": "2026-10-16",
            "executions": [
                _execution(id=1, orderId=1, side=0, price="21000", creationTimestamp="2026-10-16T09:30:00Z"),
                _execution(id=2, orderId=1, side=1, price="21050", creationTimestamp="2026-10-16T10:00:00Z"),
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()

    assert body["summary"]["candidate_plan_matches"] == 0
    assert body["summary"]["unplanned_groups"] == 1
    group = body["fill_groups"][0]
    assert group["plan_match_status"] == "unplanned"
    assert group["candidate_trade_ids"] == []


@pytest.mark.asyncio
async def test_preview_excludes_an_own_trade_explicitly_assigned_to_a_different_account(
    client: AsyncClient, db_session: AsyncSession
):
    """A trader's OWN trade, explicitly tagged account_id=999999, must not
    be proposed as a candidate when they preview a different account's
    (28592949) executions -- a Trade known to belong to one account must
    never leak into a different account's reconciliation."""
    headers = await _register_and_auth_headers(client, email="multi-account@example.com")
    day = await _open_day(client, headers)
    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json={
            "symbol": "MNQ",
            "direction": "long",
            "entry_price": "21000",
            "initial_quantity": 2,
            "entry_time": "2026-10-16T09:30:00Z",
            "setup": "Breakout",
        },
    )
    trade_id = create_resp.json()["id"]
    trade = (await db_session.execute(select(Trade).where(Trade.id == trade_id))).scalar_one()
    trade.account_id = "999999"
    await db_session.flush()

    response = await client.post(
        PREVIEW_URL,
        headers=headers,
        json={
            "account_id": 28592949,
            "date": "2026-10-16",
            "executions": [
                _execution(id=1, orderId=1, side=0, price="21000", creationTimestamp="2026-10-16T09:30:00Z"),
                _execution(id=2, orderId=1, side=1, price="21050", creationTimestamp="2026-10-16T10:00:00Z"),
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()

    group = body["fill_groups"][0]
    assert group["plan_match_status"] == "unplanned"
    assert trade_id not in group["candidate_trade_ids"]


@pytest.mark.asyncio
async def test_preview_never_mutates_an_existing_trade_it_matches_as_a_candidate(
    client: AsyncClient, db_session: AsyncSession
):
    """Row-count-unchanged (test_preview_makes_zero_database_writes) can't
    detect an UPDATE that doesn't change row counts. This re-fetches the
    matched Trade's full field set before and after a successful
    candidate-match preview and asserts nothing on it changed at all."""
    headers = await _register_and_auth_headers(client, email="no-mutation@example.com")
    day = await _open_day(client, headers)
    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json={
            "symbol": "MNQ",
            "direction": "long",
            "entry_price": "21000",
            "initial_quantity": 2,
            "entry_time": "2026-10-16T09:30:00Z",
            "setup": "Breakout",
        },
    )
    trade_id = create_resp.json()["id"]

    before = (await client.get(f"/api/v1/journal/days/{day}/trades/{trade_id}", headers=headers)).json()

    response = await client.post(
        PREVIEW_URL,
        headers=headers,
        json={
            "account_id": 28592949,
            "date": "2026-10-16",
            "executions": [
                _execution(id=1, orderId=1, side=0, price="21000", creationTimestamp="2026-10-16T09:30:00Z"),
                _execution(id=2, orderId=1, side=1, price="21050", creationTimestamp="2026-10-16T10:00:00Z"),
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["summary"]["candidate_plan_matches"] == 1  # confirms it really was matched

    await db_session.commit()  # ensure we read back via a fresh query, not session-cached state
    after = (await client.get(f"/api/v1/journal/days/{day}/trades/{trade_id}", headers=headers)).json()

    assert before == after


@pytest.mark.asyncio
async def test_preview_account_id_is_a_client_supplied_label_not_a_verified_identity(client: AsyncClient):
    """Investigation finding: nowhere in this codebase is a broker
    account_id checked against any record of which account actually
    belongs to the authenticated user -- no such mapping exists anywhere
    (confirmed by inspecting every model/schema that references
    account_id). This test documents the actual, SAFE consequence of that
    gap for this read-only endpoint: a user can claim any account_id they
    like, but every candidate/duplicate result still comes only from
    their OWN journal (scoped by user_id, not account_id) -- so the gap
    does not leak another user's data. It does mean account_id itself
    carries no ownership guarantee; see the tracked follow-up issue for
    why that matters once a future slice ever writes data keyed by it."""
    headers = await _register_and_auth_headers(client, email="unverified-account@example.com")
    day = await _open_day(client, headers)
    await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json={
            "symbol": "MNQ",
            "direction": "long",
            "entry_price": "21000",
            "initial_quantity": 2,
            "entry_time": "2026-10-16T09:30:00Z",
            "setup": "Breakout",
        },
    )

    # An account_id this user has never used anywhere, no prior association
    # of any kind -- the endpoint accepts it with no ownership check at all.
    arbitrary_account_id = 1  # smallest valid value per the schema's gt=0
    response = await client.post(
        PREVIEW_URL,
        headers=headers,
        json={
            "account_id": arbitrary_account_id,
            "date": "2026-10-16",
            "executions": [
                _execution(id=1, accountId=arbitrary_account_id, orderId=1, side=0, price="21000", creationTimestamp="2026-10-16T09:30:00Z"),
                _execution(id=2, accountId=arbitrary_account_id, orderId=1, side=1, price="21050", creationTimestamp="2026-10-16T10:00:00Z"),
            ],
        },
    )
    # Accepted (no ownership check exists) -- but still only ever matches
    # this user's own trade (account_id=None on it, so it's eligible for
    # any requested account), never anyone else's.
    assert response.status_code == 200
    assert response.json()["summary"]["candidate_plan_matches"] == 1
