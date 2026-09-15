"""Instrument multiplier endpoint tests (VS3)."""
import pytest
from httpx import AsyncClient

from app.core.instruments import INSTRUMENT_MULTIPLIERS


async def _register_and_auth_headers(client: AsyncClient, email: str = "trader@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_multipliers_require_auth(client: AsyncClient):
    response = await client.get("/api/v1/instruments/multipliers")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_multipliers_match_the_single_source_of_truth(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.get("/api/v1/instruments/multipliers", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["MNQ"] == "2"
    assert data["MES"] == "5"
    # Every table entry round-trips; the frontend must never hard-code these.
    assert set(data.keys()) == set(INSTRUMENT_MULTIPLIERS.keys())
    for symbol, value in INSTRUMENT_MULTIPLIERS.items():
        assert data[symbol] == str(value)
