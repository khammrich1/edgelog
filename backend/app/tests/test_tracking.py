"""Page-view tracking beacon tests. Must work identically for logged-in and
anonymous visitors, and must never fail the caller."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.page_view import PageView


async def _register_and_auth_headers(client: AsyncClient, email: str = "tracker@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_track_pageview_authenticated_records_the_user(client: AsyncClient, db_session: AsyncSession):
    headers = await _register_and_auth_headers(client)

    response = await client.post("/api/v1/track/pageview", headers=headers, json={"path": "/journal"})
    assert response.status_code == 204

    result = await db_session.execute(select(PageView).where(PageView.path == "/journal"))
    row = result.scalar_one()
    assert row.user_id is not None


@pytest.mark.asyncio
async def test_track_pageview_anonymous_records_no_user(client: AsyncClient, db_session: AsyncSession):
    response = await client.post("/api/v1/track/pageview", json={"path": "/login"})
    assert response.status_code == 204

    result = await db_session.execute(select(PageView).where(PageView.path == "/login"))
    row = result.scalar_one()
    assert row.user_id is None


@pytest.mark.asyncio
async def test_track_pageview_with_garbage_token_still_succeeds_as_anonymous(
    client: AsyncClient, db_session: AsyncSession
):
    response = await client.post(
        "/api/v1/track/pageview",
        headers={"Authorization": "Bearer not-a-real-token"},
        json={"path": "/settings"},
    )
    assert response.status_code == 204

    result = await db_session.execute(select(PageView).where(PageView.path == "/settings"))
    row = result.scalar_one()
    assert row.user_id is None


@pytest.mark.asyncio
async def test_track_pageview_rejects_malformed_body(client: AsyncClient):
    response = await client.post("/api/v1/track/pageview", json={})
    assert response.status_code == 422
