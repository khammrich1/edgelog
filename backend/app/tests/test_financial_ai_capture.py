"""Financial Tracker screenshot capture endpoint tests. The real Claude API
is never called here -- app.api.v1.financial_ai_capture._extract_financial_entry_via_claude
is monkeypatched in every test that reaches it."""
import pytest
from httpx import AsyncClient

import app.api.v1.financial_ai_capture as financial_ai_capture


async def _register_and_auth_headers(client: AsyncClient, email: str = "finshot@example.com") -> dict:
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
async def test_parse_financial_screenshot_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/financial-entries/parse-screenshot",
        files={"file": ("receipt.png", _tiny_png_bytes(), "image/png")},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_parse_financial_screenshot_returns_extracted_fields(client: AsyncClient, monkeypatch):
    headers = await _register_and_auth_headers(client)

    def fake_extract(image_bytes: bytes, content_type: str) -> dict:
        assert content_type == "image/png"
        return {
            "entry_type": "expense",
            "category": "evaluation fee",
            "amount": "149.00",
            "date": "2026-02-01",
            "firm": "TopStep",
            "notes": None,
        }

    monkeypatch.setattr(financial_ai_capture, "_extract_financial_entry_via_claude", fake_extract)

    response = await client.post(
        "/api/v1/financial-entries/parse-screenshot",
        headers=headers,
        files={"file": ("receipt.png", _tiny_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["entry_type"] == "expense"
    assert data["category"] == "evaluation fee"
    assert data["amount"] == "149.00"
    assert data["date"] == "2026-02-01"
    assert data["firm"] == "TopStep"
    assert data["notes"] is None


@pytest.mark.asyncio
async def test_parse_financial_screenshot_missing_api_key_returns_503(client: AsyncClient, monkeypatch):
    headers = await _register_and_auth_headers(client)
    monkeypatch.setattr(financial_ai_capture.settings, "ANTHROPIC_API_KEY", "")

    response = await client.post(
        "/api/v1/financial-entries/parse-screenshot",
        headers=headers,
        files={"file": ("receipt.png", _tiny_png_bytes(), "image/png")},
    )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_parse_financial_screenshot_rejects_unsupported_image_type(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    response = await client.post(
        "/api/v1/financial-entries/parse-screenshot",
        headers=headers,
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_parse_financial_screenshot_rejects_oversized_image(client: AsyncClient, monkeypatch):
    headers = await _register_and_auth_headers(client)
    monkeypatch.setattr(financial_ai_capture, "MAX_UPLOAD_BYTES", 10)

    response = await client.post(
        "/api/v1/financial-entries/parse-screenshot",
        headers=headers,
        files={"file": ("receipt.png", _tiny_png_bytes(), "image/png")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_parse_financial_screenshot_extraction_partial_nulls_are_allowed(client: AsyncClient, monkeypatch):
    headers = await _register_and_auth_headers(client)

    def fake_extract(image_bytes: bytes, content_type: str) -> dict:
        return {
            "entry_type": None,
            "category": None,
            "amount": None,
            "date": None,
            "firm": None,
            "notes": "Screenshot was too blurry to read most fields.",
        }

    monkeypatch.setattr(financial_ai_capture, "_extract_financial_entry_via_claude", fake_extract)

    response = await client.post(
        "/api/v1/financial-entries/parse-screenshot",
        headers=headers,
        files={"file": ("receipt.png", _tiny_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["entry_type"] is None
    assert data["notes"] == "Screenshot was too blurry to read most fields."


# ---- Bulk (multi-row table) extraction ----


@pytest.mark.asyncio
async def test_parse_financial_screenshot_bulk_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/financial-entries/parse-screenshot-bulk",
        files={"file": ("payouts.png", _tiny_png_bytes(), "image/png")},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_parse_financial_screenshot_bulk_returns_multiple_rows(client: AsyncClient, monkeypatch):
    headers = await _register_and_auth_headers(client)

    def fake_extract_bulk(image_bytes: bytes, content_type: str) -> list:
        assert content_type == "image/png"
        return [
            {
                "entry_type": "income",
                "category": "payout",
                "amount": "450.00",
                "date": "2026-06-18",
                "firm": None,
                "notes": None,
            },
            {
                "entry_type": "income",
                "category": "payout",
                "amount": "480.00",
                "date": "2026-06-12",
                "firm": None,
                "notes": None,
            },
            {
                "entry_type": "income",
                "category": "payout",
                "amount": "295.00",
                "date": "2026-05-01",
                "firm": None,
                "notes": "Requested amount differed from the finalized payout amount.",
            },
        ]

    monkeypatch.setattr(financial_ai_capture, "_extract_financial_entries_bulk_via_claude", fake_extract_bulk)

    response = await client.post(
        "/api/v1/financial-entries/parse-screenshot-bulk",
        headers=headers,
        files={"file": ("payouts.png", _tiny_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert [row["amount"] for row in data] == ["450.00", "480.00", "295.00"]
    assert all(row["entry_type"] == "income" for row in data)


@pytest.mark.asyncio
async def test_parse_financial_screenshot_bulk_missing_api_key_returns_503(client: AsyncClient, monkeypatch):
    headers = await _register_and_auth_headers(client)
    monkeypatch.setattr(financial_ai_capture.settings, "ANTHROPIC_API_KEY", "")

    response = await client.post(
        "/api/v1/financial-entries/parse-screenshot-bulk",
        headers=headers,
        files={"file": ("payouts.png", _tiny_png_bytes(), "image/png")},
    )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_parse_financial_screenshot_bulk_rejects_unsupported_image_type(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    response = await client.post(
        "/api/v1/financial-entries/parse-screenshot-bulk",
        headers=headers,
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_parse_financial_screenshot_bulk_rejects_oversized_image(client: AsyncClient, monkeypatch):
    headers = await _register_and_auth_headers(client)
    monkeypatch.setattr(financial_ai_capture, "MAX_UPLOAD_BYTES", 10)

    response = await client.post(
        "/api/v1/financial-entries/parse-screenshot-bulk",
        headers=headers,
        files={"file": ("payouts.png", _tiny_png_bytes(), "image/png")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_parse_financial_screenshot_bulk_single_row_still_returns_a_list(client: AsyncClient, monkeypatch):
    headers = await _register_and_auth_headers(client)

    def fake_extract_bulk(image_bytes: bytes, content_type: str) -> list:
        return [
            {
                "entry_type": "expense",
                "category": "evaluation fee",
                "amount": "149.00",
                "date": "2026-02-01",
                "firm": "TopStep",
                "notes": None,
            }
        ]

    monkeypatch.setattr(financial_ai_capture, "_extract_financial_entries_bulk_via_claude", fake_extract_bulk)

    response = await client.post(
        "/api/v1/financial-entries/parse-screenshot-bulk",
        headers=headers,
        files={"file": ("receipt.png", _tiny_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["category"] == "evaluation fee"


@pytest.mark.asyncio
async def test_parse_financial_screenshot_bulk_flags_possible_duplicates(client: AsyncClient, monkeypatch):
    headers = await _register_and_auth_headers(client, email="findupe@example.com")

    await client.post(
        "/api/v1/financial-entries",
        headers=headers,
        json={"entry_type": "income", "category": "payout", "amount": "450.00", "date": "2026-06-18"},
    )

    def fake_extract_bulk(image_bytes: bytes, content_type: str) -> list:
        return [
            {
                "entry_type": "income",
                "category": "payout",
                "amount": "450.00",
                "date": "2026-06-18",
                "firm": None,
                "notes": None,
            },
            {
                "entry_type": "income",
                "category": "payout",
                "amount": "480.00",
                "date": "2026-06-12",
                "firm": None,
                "notes": None,
            },
        ]

    monkeypatch.setattr(financial_ai_capture, "_extract_financial_entries_bulk_via_claude", fake_extract_bulk)

    response = await client.post(
        "/api/v1/financial-entries/parse-screenshot-bulk",
        headers=headers,
        files={"file": ("payouts.png", _tiny_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data[0]["possible_duplicate"] is True
    assert data[1]["possible_duplicate"] is False


@pytest.mark.asyncio
async def test_parse_financial_screenshot_bulk_duplicate_check_is_scoped_to_the_user(
    client: AsyncClient, monkeypatch
):
    headers_a = await _register_and_auth_headers(client, email="findupe_a@example.com")
    headers_b = await _register_and_auth_headers(client, email="findupe_b@example.com")

    await client.post(
        "/api/v1/financial-entries",
        headers=headers_a,
        json={"entry_type": "income", "category": "payout", "amount": "450.00", "date": "2026-06-18"},
    )

    def fake_extract_bulk(image_bytes: bytes, content_type: str) -> list:
        return [
            {
                "entry_type": "income",
                "category": "payout",
                "amount": "450.00",
                "date": "2026-06-18",
                "firm": None,
                "notes": None,
            }
        ]

    monkeypatch.setattr(financial_ai_capture, "_extract_financial_entries_bulk_via_claude", fake_extract_bulk)

    response = await client.post(
        "/api/v1/financial-entries/parse-screenshot-bulk",
        headers=headers_b,
        files={"file": ("payouts.png", _tiny_png_bytes(), "image/png")},
    )

    assert response.json()[0]["possible_duplicate"] is False


@pytest.mark.asyncio
async def test_parse_financial_screenshot_bulk_duplicate_check_tolerates_null_fields(
    client: AsyncClient, monkeypatch
):
    headers = await _register_and_auth_headers(client, email="findupe_null@example.com")

    def fake_extract_bulk(image_bytes: bytes, content_type: str) -> list:
        return [
            {"entry_type": None, "category": None, "amount": None, "date": None, "firm": None, "notes": None}
        ]

    monkeypatch.setattr(financial_ai_capture, "_extract_financial_entries_bulk_via_claude", fake_extract_bulk)

    response = await client.post(
        "/api/v1/financial-entries/parse-screenshot-bulk",
        headers=headers,
        files={"file": ("payouts.png", _tiny_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    assert response.json()[0]["possible_duplicate"] is False
