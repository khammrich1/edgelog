"""Instrument multiplier endpoint tests (VS3)."""
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.core.instruments import INSTRUMENT_MULTIPLIERS, get_multiplier


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


def test_get_multiplier_resolves_bare_root():
    assert get_multiplier("MNQ") == Decimal("2")
    assert get_multiplier(" mnq ") == Decimal("2")


def test_get_multiplier_resolves_dated_futures_contract_to_its_root():
    # Root + single-letter month code + 1-4 digit year (CME convention).
    assert get_multiplier("MNQZ26") == Decimal("2")
    assert get_multiplier("mnqz26") == Decimal("2")
    assert get_multiplier("NQZ26") == Decimal("20")
    assert get_multiplier("ESH25") == Decimal("50")
    assert get_multiplier("MCLZ2026") == Decimal("100")
    assert get_multiplier("MGCG6") == Decimal("10")


def test_get_multiplier_returns_none_for_unknown_symbol_and_unknown_dated_contract():
    assert get_multiplier("XYZ") is None
    assert get_multiplier("XYZZ26") is None
