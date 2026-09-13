"""AI screenshot trade capture endpoint tests (VS3). The real Claude API is
never called here -- app.api.v1.ai_capture._extract_trade_details_via_claude
is monkeypatched in every test that reaches it."""
import pytest
from httpx import AsyncClient

import app.api.v1.ai_capture as ai_capture


async def _register_and_auth_headers(client: AsyncClient, email: str = "shooter@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _tiny_png_bytes() -> bytes:
    # A minimal valid 1x1 transparent PNG.
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )


@pytest.mark.asyncio
async def test_parse_screenshot_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/trades/parse-screenshot",
        files={"file": ("chart.png", _tiny_png_bytes(), "image/png")},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_parse_screenshot_returns_extracted_fields(client: AsyncClient, monkeypatch):
    headers = await _register_and_auth_headers(client)

    def fake_extract(image_bytes: bytes, content_type: str) -> dict:
        assert content_type == "image/png"
        return {
            "symbol": "MNQ",
            "direction": "long",
            "entry_price": "24500.25",
            "stop_price": "24480",
            "target_price": "24560",
            "initial_quantity": 3,
            "notes": None,
        }

    monkeypatch.setattr(ai_capture, "_extract_trade_details_via_claude", fake_extract)

    response = await client.post(
        "/api/v1/trades/parse-screenshot",
        headers=headers,
        files={"file": ("chart.png", _tiny_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "MNQ"
    assert data["direction"] == "long"
    assert data["entry_price"] == "24500.25"
    assert data["initial_quantity"] == 3
    assert data["notes"] is None


@pytest.mark.asyncio
async def test_parse_screenshot_missing_api_key_returns_503(client: AsyncClient, monkeypatch):
    headers = await _register_and_auth_headers(client)
    monkeypatch.setattr(ai_capture.settings, "ANTHROPIC_API_KEY", "")

    response = await client.post(
        "/api/v1/trades/parse-screenshot",
        headers=headers,
        files={"file": ("chart.png", _tiny_png_bytes(), "image/png")},
    )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_parse_screenshot_rejects_unsupported_image_type(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    response = await client.post(
        "/api/v1/trades/parse-screenshot",
        headers=headers,
        files={"file": ("chart.gif", b"not a real gif", "image/gif")},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_parse_screenshot_rejects_oversized_image(client: AsyncClient, monkeypatch):
    headers = await _register_and_auth_headers(client)
    monkeypatch.setattr(ai_capture, "MAX_UPLOAD_BYTES", 10)

    response = await client.post(
        "/api/v1/trades/parse-screenshot",
        headers=headers,
        files={"file": ("chart.png", _tiny_png_bytes(), "image/png")},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_parse_screenshot_extraction_partial_nulls_are_allowed(client: AsyncClient, monkeypatch):
    headers = await _register_and_auth_headers(client)

    def fake_extract(image_bytes: bytes, content_type: str) -> dict:
        return {
            "symbol": None,
            "direction": None,
            "entry_price": None,
            "stop_price": None,
            "target_price": None,
            "initial_quantity": None,
            "notes": "Screenshot was too blurry to read most fields.",
        }

    monkeypatch.setattr(ai_capture, "_extract_trade_details_via_claude", fake_extract)

    response = await client.post(
        "/api/v1/trades/parse-screenshot",
        headers=headers,
        files={"file": ("chart.png", _tiny_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] is None
    assert data["notes"] == "Screenshot was too blurry to read most fields."
