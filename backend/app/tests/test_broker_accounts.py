"""Tests for the broker-account ownership registry (issue #95).

Covers the deliverable's explicit acceptance list: correct ownership,
wrong-user denial, arbitrary/forged IDs, multiple accounts per user, and
legacy (pre-existing, unrelated Trade.account_id) behavior. Also a direct
migration/constraint test proving the partial "at most one verified
claim per account" index actually enforces at the database level, even
though nothing in this slice ever produces a verified row through the API."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import app.api.v1.broker_accounts as broker_accounts_module
from app.models.broker_accounts import BrokerAccount
from app.models.trades import Trade
from app.models.user import User

BASE = "/api/v1/broker-accounts"


async def _register_and_auth_headers(client: AsyncClient, email: str) -> dict:
    response = await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_requires_authentication(client: AsyncClient):
    response = await client.post(BASE, json={"provider": "topstepx", "account_id": "123"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_and_list_round_trip_is_always_unverified(client: AsyncClient):
    headers = await _register_and_auth_headers(client, "owner@example.com")

    create_resp = await client.post(
        BASE, headers=headers, json={"provider": "topstepx", "account_id": "28592949", "label": "Practice 50K"}
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["provider"] == "topstepx"
    assert body["account_id"] == "28592949"
    assert body["label"] == "Practice 50K"
    assert body["verification_status"] == "unverified"
    assert body["verified_at"] is None

    list_resp = await client.get(BASE, headers=headers)
    assert list_resp.status_code == 200
    accounts = list_resp.json()
    assert len(accounts) == 1
    assert accounts[0]["id"] == body["id"]


@pytest.mark.asyncio
async def test_a_user_can_register_multiple_distinct_accounts(client: AsyncClient):
    headers = await _register_and_auth_headers(client, "multi@example.com")

    for account_id in ("111", "222", "333"):
        resp = await client.post(BASE, headers=headers, json={"provider": "topstepx", "account_id": account_id})
        assert resp.status_code == 201

    accounts = (await client.get(BASE, headers=headers)).json()
    assert {a["account_id"] for a in accounts} == {"111", "222", "333"}
    assert all(a["verification_status"] == "unverified" for a in accounts)


@pytest.mark.asyncio
async def test_registering_the_same_account_twice_is_rejected_as_a_duplicate(client: AsyncClient):
    headers = await _register_and_auth_headers(client, "dup@example.com")
    await client.post(BASE, headers=headers, json={"provider": "topstepx", "account_id": "999"})

    second = await client.post(BASE, headers=headers, json={"provider": "topstepx", "account_id": "999"})
    assert second.status_code == 409

    accounts = (await client.get(BASE, headers=headers)).json()
    assert len(accounts) == 1  # the duplicate attempt created nothing


@pytest.mark.asyncio
async def test_an_arbitrary_forged_account_id_is_accepted_but_only_ever_unverified(client: AsyncClient):
    """Registering is a self-report, not an ownership check -- any string
    is accepted as a label, and it is never anything but unverified."""
    headers = await _register_and_auth_headers(client, "forged@example.com")

    resp = await client.post(BASE, headers=headers, json={"provider": "topstepx", "account_id": "not-a-real-account-999999"})
    assert resp.status_code == 201
    assert resp.json()["verification_status"] == "unverified"


@pytest.mark.asyncio
async def test_two_different_users_can_each_register_the_same_account_id_unverified(client: AsyncClient):
    """With no verification mechanism, there is nothing to arbitrate a
    collision with -- both self-reports are retained, both unverified."""
    headers_a = await _register_and_auth_headers(client, "claim-a@example.com")
    headers_b = await _register_and_auth_headers(client, "claim-b@example.com")

    resp_a = await client.post(BASE, headers=headers_a, json={"provider": "topstepx", "account_id": "555"})
    resp_b = await client.post(BASE, headers=headers_b, json={"provider": "topstepx", "account_id": "555"})

    assert resp_a.status_code == 201
    assert resp_b.status_code == 201
    assert resp_a.json()["verification_status"] == "unverified"
    assert resp_b.json()["verification_status"] == "unverified"


@pytest.mark.asyncio
async def test_a_user_cannot_see_another_users_registered_accounts(client: AsyncClient):
    headers_a = await _register_and_auth_headers(client, "isolated-a@example.com")
    headers_b = await _register_and_auth_headers(client, "isolated-b@example.com")

    await client.post(BASE, headers=headers_a, json={"provider": "topstepx", "account_id": "777"})

    list_b = (await client.get(BASE, headers=headers_b)).json()
    assert list_b == []


@pytest.mark.asyncio
async def test_a_user_cannot_delete_another_users_registered_account(client: AsyncClient):
    headers_a = await _register_and_auth_headers(client, "delete-a@example.com")
    headers_b = await _register_and_auth_headers(client, "delete-b@example.com")

    created = await client.post(BASE, headers=headers_a, json={"provider": "topstepx", "account_id": "888"})
    account_id = created.json()["id"]

    denied = await client.delete(f"{BASE}/{account_id}", headers=headers_b)
    assert denied.status_code == 404  # not found, not "forbidden" -- never confirms it exists for another user

    still_there = (await client.get(BASE, headers=headers_a)).json()
    assert len(still_there) == 1


@pytest.mark.asyncio
async def test_a_user_can_delete_their_own_registered_account(client: AsyncClient):
    headers = await _register_and_auth_headers(client, "self-delete@example.com")
    created = await client.post(BASE, headers=headers, json={"provider": "topstepx", "account_id": "444"})
    account_id = created.json()["id"]

    resp = await client.delete(f"{BASE}/{account_id}", headers=headers)
    assert resp.status_code == 204

    accounts = (await client.get(BASE, headers=headers)).json()
    assert accounts == []


@pytest.mark.asyncio
async def test_rejects_malformed_create_payload(client: AsyncClient):
    headers = await _register_and_auth_headers(client, "malformed@example.com")
    resp = await client.post(BASE, headers=headers, json={"provider": "topstepx"})  # missing account_id
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_registering_a_broker_account_does_not_touch_existing_trades(client: AsyncClient, db_session: AsyncSession):
    """Legacy-behavior check: Trade.account_id (migration 011, still
    unwritten by any trade route) must stay exactly as it is -- this
    slice creates no backfill, and a trade's own account_id is untouched
    by registering a BrokerAccount row."""
    headers = await _register_and_auth_headers(client, "legacy@example.com")
    day = "2026-10-20"
    await client.get(f"/api/v1/journal/days/{day}", headers=headers)
    create_resp = await client.post(
        f"/api/v1/journal/days/{day}/trades",
        headers=headers,
        json={
            "symbol": "MNQ",
            "direction": "long",
            "entry_price": "21000",
            "initial_quantity": 2,
            "entry_time": "2026-10-20T09:30:00Z",
            "setup": "Breakout",
        },
    )
    trade_id = create_resp.json()["id"]

    await client.post(BASE, headers=headers, json={"provider": "topstepx", "account_id": "28592949"})

    trade = (await db_session.execute(select(Trade).where(Trade.id == trade_id))).scalar_one()
    assert trade.account_id is None  # untouched -- no backfill, no silent certification


async def _make_user(db_session: AsyncSession, email: str) -> User:
    user = User(email=email, password_hash="not-a-real-hash")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_only_one_verified_claim_per_account_id_is_allowed_at_the_database_level(db_session: AsyncSession):
    """Direct model/constraint test: the partial unique index must refuse
    a second VERIFIED row for the same (provider, account_id) even
    though no API route in this slice can ever produce one. This proves
    the constraint itself is correctly in place for whenever real
    verification exists."""
    user_a = await _make_user(db_session, "constraint-a@example.com")
    user_b = await _make_user(db_session, "constraint-b@example.com")

    first = BrokerAccount(
        user_id=user_a.id, provider="topstepx", account_id="shared-verified-id", verification_status="verified"
    )
    db_session.add(first)
    await db_session.flush()

    second = BrokerAccount(
        user_id=user_b.id, provider="topstepx", account_id="shared-verified-id", verification_status="verified"
    )
    db_session.add(second)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_two_unverified_rows_for_the_same_account_id_do_not_violate_the_verified_only_index(
    db_session: AsyncSession,
):
    """The partial index only constrains verified rows -- two unverified
    claims on the same (provider, account_id), from different users,
    must coexist without error (mirrors the API-level duplicate-claim
    test above, exercised directly at the model layer)."""
    user_a = await _make_user(db_session, "unverified-a@example.com")
    user_b = await _make_user(db_session, "unverified-b@example.com")

    first = BrokerAccount(
        user_id=user_a.id, provider="topstepx", account_id="shared-unverified-id", verification_status="unverified"
    )
    second = BrokerAccount(
        user_id=user_b.id, provider="topstepx", account_id="shared-unverified-id", verification_status="unverified"
    )
    db_session.add_all([first, second])
    await db_session.flush()  # must not raise


# --- Owner review follow-up (PR #98): normalization + race safety ---


@pytest.mark.asyncio
async def test_provider_is_normalized_to_lowercase_and_whitespace_trimmed(client: AsyncClient):
    headers = await _register_and_auth_headers(client, "normalize-provider@example.com")

    resp = await client.post(BASE, headers=headers, json={"provider": "  TopstepX  ", "account_id": "123"})
    assert resp.status_code == 201
    assert resp.json()["provider"] == "topstepx"


@pytest.mark.asyncio
async def test_account_id_is_whitespace_trimmed_but_not_case_folded(client: AsyncClient):
    headers = await _register_and_auth_headers(client, "normalize-account@example.com")

    resp = await client.post(BASE, headers=headers, json={"provider": "topstepx", "account_id": "  AbC123  "})
    assert resp.status_code == 201
    assert resp.json()["account_id"] == "AbC123"  # trimmed, casing preserved -- opaque broker identifier


@pytest.mark.asyncio
async def test_differently_cased_provider_collides_with_an_existing_registration(client: AsyncClient):
    """The exact bypass the owner review flagged: "TopstepX" vs
    "topstepx" must not be able to register as two separate rows for
    what is, after normalization, the same claim."""
    headers = await _register_and_auth_headers(client, "collide-provider@example.com")
    first = await client.post(BASE, headers=headers, json={"provider": "topstepx", "account_id": "456"})
    assert first.status_code == 201

    second = await client.post(BASE, headers=headers, json={"provider": "TopstepX", "account_id": "456"})
    assert second.status_code == 409

    accounts = (await client.get(BASE, headers=headers)).json()
    assert len(accounts) == 1


@pytest.mark.asyncio
async def test_padded_account_id_collides_with_an_existing_registration(client: AsyncClient):
    headers = await _register_and_auth_headers(client, "collide-account@example.com")
    first = await client.post(BASE, headers=headers, json={"provider": "topstepx", "account_id": "789"})
    assert first.status_code == 201

    second = await client.post(BASE, headers=headers, json={"provider": "topstepx", "account_id": "  789  "})
    assert second.status_code == 409

    accounts = (await client.get(BASE, headers=headers)).json()
    assert len(accounts) == 1


@pytest.mark.asyncio
async def test_whitespace_only_provider_or_account_id_is_rejected(client: AsyncClient):
    headers = await _register_and_auth_headers(client, "blank-fields@example.com")

    blank_provider = await client.post(BASE, headers=headers, json={"provider": "   ", "account_id": "123"})
    assert blank_provider.status_code == 422

    blank_account = await client.post(BASE, headers=headers, json={"provider": "topstepx", "account_id": "   "})
    assert blank_account.status_code == 422


@pytest.mark.asyncio
async def test_concurrent_duplicate_registration_returns_409_not_500(
    client: AsyncClient, test_engine: AsyncEngine, monkeypatch
):
    """Simulates the race the owner review flagged: another request's
    INSERT commits in the window between this request's pre-check SELECT
    and its own INSERT. The route's pre-check is monkeypatched to report
    "nothing found" (exactly what a losing race would see), so only the
    database's own unique index is left standing between this request
    and a duplicate row -- proving the INSERT path itself converts that
    conflict into 409, not an unhandled 500.

    Built entirely on a second, independently-committed session (not
    the shared, never-committed db_session the test client's requests
    run on) so the "pre-existing" row is genuinely visible to a *new*
    transaction the way a real concurrent request's commit would be --
    not an artifact of sharing one uncommitted test transaction."""
    from app.core.security import create_access_token

    IndependentSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with IndependentSession() as other_session:
        user = User(email="race@example.com", password_hash="not-a-real-hash")
        other_session.add(user)
        await other_session.flush()
        other_session.add(
            BrokerAccount(user_id=user.id, provider="topstepx", account_id="race-123", verification_status="unverified")
        )
        await other_session.commit()
        user_id = user.id

    token = create_access_token({"sub": str(user_id), "email": "race@example.com"})
    headers = {"Authorization": f"Bearer {token}"}

    async def _report_nothing_found(*args, **kwargs):
        return None

    monkeypatch.setattr(broker_accounts_module, "_find_existing_claim", _report_nothing_found)

    response = await client.post(BASE, headers=headers, json={"provider": "topstepx", "account_id": "race-123"})

    assert response.status_code == 409
    assert "already registered" in response.json()["detail"].lower()
