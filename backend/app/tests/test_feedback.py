"""User-submitted feedback endpoint tests."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback


async def _register_and_auth_headers(client: AsyncClient, email: str = "feedbacker@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_submit_feedback_requires_auth(client: AsyncClient):
    response = await client.post("/api/v1/feedback", json={"message": "Hello"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_submit_feedback_creates_a_row_tied_to_the_user(client: AsyncClient, db_session: AsyncSession):
    headers = await _register_and_auth_headers(client)
    response = await client.post("/api/v1/feedback", headers=headers, json={"message": "Love the calendar view"})
    assert response.status_code == 201

    result = await db_session.execute(select(Feedback).where(Feedback.message == "Love the calendar view"))
    row = result.scalar_one()
    assert row.user_id is not None


@pytest.mark.asyncio
async def test_submit_feedback_rejects_empty_message(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.post("/api/v1/feedback", headers=headers, json={"message": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_feedback_rejects_overlong_message(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.post("/api/v1/feedback", headers=headers, json={"message": "x" * 2001})
    assert response.status_code == 422
