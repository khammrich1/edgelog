"""Admin page endpoint tests: account roster, traffic, feedback. All three
routes are admin-gated -- there's no promote-to-admin API by design, so
tests flip is_admin directly on the model via db_session."""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback
from app.models.page_view import PageView
from app.models.user import User


async def _register_and_auth_headers(client: AsyncClient, email: str) -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _make_admin(db_session: AsyncSession, email: str) -> None:
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    user.is_admin = True
    await db_session.commit()


@pytest.mark.asyncio
async def test_admin_routes_require_auth(client: AsyncClient):
    assert (await client.get("/api/v1/admin/roster")).status_code == 403
    assert (await client.get("/api/v1/admin/traffic")).status_code == 403
    assert (await client.get("/api/v1/admin/feedback")).status_code == 403


@pytest.mark.asyncio
async def test_admin_routes_reject_non_admin_user(client: AsyncClient):
    headers = await _register_and_auth_headers(client, "notadmin@example.com")

    assert (await client.get("/api/v1/admin/roster", headers=headers)).status_code == 403
    assert (await client.get("/api/v1/admin/traffic", headers=headers)).status_code == 403
    assert (await client.get("/api/v1/admin/feedback", headers=headers)).status_code == 403


@pytest.mark.asyncio
async def test_roster_lists_users_with_last_activity(client: AsyncClient, db_session: AsyncSession):
    admin_headers = await _register_and_auth_headers(client, "admin@example.com")
    await _make_admin(db_session, "admin@example.com")

    other_headers = await _register_and_auth_headers(client, "trader@example.com")
    other_id_response = await client.get("/api/v1/auth/me", headers=other_headers)
    other_id = other_id_response.json()["id"]

    db_session.add(PageView(user_id=other_id, path="/journal", created_at=datetime.now(timezone.utc) - timedelta(days=2)))
    db_session.add(PageView(user_id=other_id, path="/financials", created_at=datetime.now(timezone.utc)))
    await db_session.commit()

    response = await client.get("/api/v1/admin/roster", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    by_email = {row["email"]: row for row in data}
    assert by_email["admin@example.com"]["is_admin"] is True
    assert by_email["admin@example.com"]["last_activity_path"] is None

    assert by_email["trader@example.com"]["is_admin"] is False
    # The most recent of the two seeded page views should win.
    assert by_email["trader@example.com"]["last_activity_path"] == "/financials"


@pytest.mark.asyncio
async def test_traffic_aggregates_hits_and_auth_split_within_the_window(
    client: AsyncClient, db_session: AsyncSession
):
    admin_headers = await _register_and_auth_headers(client, "admin2@example.com")
    await _make_admin(db_session, "admin2@example.com")

    other_headers = await _register_and_auth_headers(client, "trader2@example.com")
    other_id = (await client.get("/api/v1/auth/me", headers=other_headers)).json()["id"]

    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            PageView(user_id=other_id, path="/journal", created_at=now),
            PageView(user_id=other_id, path="/journal", created_at=now),
            PageView(user_id=None, path="/journal", created_at=now),
            PageView(user_id=None, path="/login", created_at=now),
            # Outside the 7-day window -- must be excluded.
            PageView(user_id=other_id, path="/journal", created_at=now - timedelta(days=10)),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/v1/admin/traffic", headers=admin_headers)
    assert response.status_code == 200
    rows = {row["path"]: row for row in response.json()}

    assert rows["/journal"]["hits"] == 3
    assert rows["/journal"]["unique_auth_users"] == 1
    assert rows["/journal"]["auth_hits"] == 2
    assert rows["/journal"]["unauth_hits"] == 1

    assert rows["/login"]["hits"] == 1
    assert rows["/login"]["unique_auth_users"] == 0
    assert rows["/login"]["auth_hits"] == 0
    assert rows["/login"]["unauth_hits"] == 1


@pytest.mark.asyncio
async def test_admin_feedback_list_is_newest_first_with_submitter_email(
    client: AsyncClient, db_session: AsyncSession
):
    admin_headers = await _register_and_auth_headers(client, "admin3@example.com")
    await _make_admin(db_session, "admin3@example.com")

    submitter_headers = await _register_and_auth_headers(client, "submitter@example.com")
    await client.post("/api/v1/feedback", headers=submitter_headers, json={"message": "First message"})
    await client.post("/api/v1/feedback", headers=submitter_headers, json={"message": "Second message"})

    response = await client.get("/api/v1/admin/feedback", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["message"] == "Second message"
    assert data[0]["user_email"] == "submitter@example.com"


@pytest.mark.asyncio
async def test_admin_feedback_survives_a_user_row_going_away(client: AsyncClient, db_session: AsyncSession):
    admin_headers = await _register_and_auth_headers(client, "admin4@example.com")
    await _make_admin(db_session, "admin4@example.com")

    db_session.add(Feedback(user_id=None, message="Anonymous-ish feedback"))
    await db_session.commit()

    response = await client.get("/api/v1/admin/feedback", headers=admin_headers)
    data = response.json()
    assert any(row["message"] == "Anonymous-ish feedback" and row["user_email"] is None for row in data)
