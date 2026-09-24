"""Annual P&L / Financial Tracker endpoint tests. A flat cash ledger,
independent of Trade/TradingDay."""
from decimal import Decimal

import pytest
from httpx import AsyncClient


async def _register_and_auth_headers(client: AsyncClient, email: str = "finance@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _base_entry_payload(**overrides):
    payload = {
        "entry_type": "expense",
        "category": "evaluation fee",
        "amount": "150",
        "date": "2026-02-01",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_financial_entries_require_auth(client: AsyncClient):
    response = await client.get(
        "/api/v1/financial-entries", params={"start": "2026-01-01", "end": "2026-12-31"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_expense_entry(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload()
    )
    assert response.status_code == 201
    data = response.json()
    assert data["entry_type"] == "expense"
    assert data["category"] == "evaluation fee"
    assert Decimal(data["amount"]) == Decimal("150.00")
    assert data["date"] == "2026-02-01"
    assert data["has_screenshot"] is False


@pytest.mark.asyncio
async def test_create_income_entry(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.post(
        "/api/v1/financial-entries",
        headers=headers,
        json=_base_entry_payload(entry_type="income", category="payout", amount="800", firm="TopStep"),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["entry_type"] == "income"
    assert data["firm"] == "TopStep"


@pytest.mark.asyncio
async def test_create_entry_rejects_non_positive_amount(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload(amount="0")
    )
    assert response.status_code == 422

    response = await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload(amount="-10")
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_bulk_create_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/financial-entries/bulk", json={"entries": [_base_entry_payload()]}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_bulk_create_multiple_entries_in_one_request(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.post(
        "/api/v1/financial-entries/bulk",
        headers=headers,
        json={
            "entries": [
                _base_entry_payload(entry_type="income", category="payout", amount="450", date="2026-06-18"),
                _base_entry_payload(entry_type="income", category="payout", amount="480", date="2026-06-12"),
                _base_entry_payload(entry_type="income", category="payout", amount="295", date="2026-05-01"),
            ]
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 3
    assert [Decimal(row["amount"]) for row in data] == [Decimal("450.00"), Decimal("480.00"), Decimal("295.00")]
    assert all(row["has_screenshot"] is False for row in data)

    list_response = await client.get(
        "/api/v1/financial-entries", headers=headers, params={"start": "2026-01-01", "end": "2026-12-31"}
    )
    assert len(list_response.json()) == 3


@pytest.mark.asyncio
async def test_bulk_create_rejects_empty_entries_list(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.post("/api/v1/financial-entries/bulk", headers=headers, json={"entries": []})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_bulk_create_rejects_more_than_max_entries(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.post(
        "/api/v1/financial-entries/bulk",
        headers=headers,
        json={"entries": [_base_entry_payload() for _ in range(101)]},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_bulk_create_rejects_whole_batch_if_one_entry_invalid(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.post(
        "/api/v1/financial-entries/bulk",
        headers=headers,
        json={"entries": [_base_entry_payload(), _base_entry_payload(amount="-10")]},
    )
    assert response.status_code == 422

    list_response = await client.get(
        "/api/v1/financial-entries", headers=headers, params={"start": "2026-01-01", "end": "2026-12-31"}
    )
    assert list_response.json() == []


@pytest.mark.asyncio
async def test_bulk_create_scopes_entries_to_the_authenticated_user(client: AsyncClient):
    headers_a = await _register_and_auth_headers(client, email="finance_bulk_a@example.com")
    headers_b = await _register_and_auth_headers(client, email="finance_bulk_b@example.com")

    await client.post(
        "/api/v1/financial-entries/bulk", headers=headers_a, json={"entries": [_base_entry_payload()]}
    )

    response = await client.get(
        "/api/v1/financial-entries", headers=headers_b, params={"start": "2026-01-01", "end": "2026-12-31"}
    )
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_entry_not_found_returns_404(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.get("/api/v1/financial-entries/999999", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_entry_user_isolation(client: AsyncClient):
    headers_a = await _register_and_auth_headers(client, email="finance_a@example.com")
    headers_b = await _register_and_auth_headers(client, email="finance_b@example.com")
    create_response = await client.post(
        "/api/v1/financial-entries", headers=headers_a, json=_base_entry_payload()
    )
    entry_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/financial-entries/{entry_id}", headers=headers_b)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_entry_partial_fields(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    create_response = await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload()
    )
    entry_id = create_response.json()["id"]

    response = await client.put(
        f"/api/v1/financial-entries/{entry_id}", headers=headers, json={"category": "platform fee"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "platform fee"
    assert data["entry_type"] == "expense"  # unchanged
    assert Decimal(data["amount"]) == Decimal("150.00")  # unchanged


@pytest.mark.asyncio
async def test_update_entry_changes_date(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    create_response = await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload(date="2026-02-01")
    )
    entry_id = create_response.json()["id"]

    await client.put(
        f"/api/v1/financial-entries/{entry_id}", headers=headers, json={"date": "2026-06-15"}
    )

    old_range = await client.get(
        "/api/v1/financial-entries", headers=headers, params={"start": "2026-01-01", "end": "2026-03-01"}
    )
    assert old_range.json() == []

    new_range = await client.get(
        "/api/v1/financial-entries", headers=headers, params={"start": "2026-06-01", "end": "2026-06-30"}
    )
    assert len(new_range.json()) == 1
    assert new_range.json()[0]["id"] == entry_id


@pytest.mark.asyncio
async def test_delete_entry(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    create_response = await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload()
    )
    entry_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/v1/financial-entries/{entry_id}", headers=headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/financial-entries/{entry_id}", headers=headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_list_entries_requires_auth(client: AsyncClient):
    response = await client.get(
        "/api/v1/financial-entries", params={"start": "2026-01-01", "end": "2026-12-31"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_entries_end_before_start_returns_400(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.get(
        "/api/v1/financial-entries", headers=headers, params={"start": "2026-12-31", "end": "2026-01-01"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "end must not be before start"


@pytest.mark.asyncio
async def test_list_entries_malformed_date_returns_422(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.get(
        "/api/v1/financial-entries", headers=headers, params={"start": "not-a-date", "end": "2026-12-31"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_entries_empty_range_returns_empty_list(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    response = await client.get(
        "/api/v1/financial-entries", headers=headers, params={"start": "2026-01-01", "end": "2026-12-31"}
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_entries_excludes_entries_outside_range(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload(date="2025-12-31")
    )
    await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload(date="2026-06-15")
    )
    await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload(date="2027-01-01")
    )

    response = await client.get(
        "/api/v1/financial-entries", headers=headers, params={"start": "2026-01-01", "end": "2026-12-31"}
    )
    data = response.json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-06-15"


@pytest.mark.asyncio
async def test_list_entries_ordered_by_date(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload(date="2026-03-01")
    )
    await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload(date="2026-01-01")
    )
    await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload(date="2026-02-01")
    )

    response = await client.get(
        "/api/v1/financial-entries", headers=headers, params={"start": "2026-01-01", "end": "2026-12-31"}
    )
    dates = [e["date"] for e in response.json()]
    assert dates == ["2026-01-01", "2026-02-01", "2026-03-01"]


@pytest.mark.asyncio
async def test_list_entries_user_isolation(client: AsyncClient):
    headers_a = await _register_and_auth_headers(client, email="finance_c@example.com")
    headers_b = await _register_and_auth_headers(client, email="finance_d@example.com")
    await client.post("/api/v1/financial-entries", headers=headers_a, json=_base_entry_payload())

    response = await client.get(
        "/api/v1/financial-entries", headers=headers_b, params={"start": "2026-01-01", "end": "2026-12-31"}
    )
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_entries_includes_both_expense_and_income(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload(entry_type="expense")
    )
    await client.post(
        "/api/v1/financial-entries",
        headers=headers,
        json=_base_entry_payload(entry_type="income", category="payout", date="2026-02-02"),
    )

    response = await client.get(
        "/api/v1/financial-entries", headers=headers, params={"start": "2026-01-01", "end": "2026-12-31"}
    )
    types = {e["entry_type"] for e in response.json()}
    assert types == {"expense", "income"}


@pytest.mark.asyncio
async def test_financial_entry_screenshot_upload_get_and_delete(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    create_response = await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload()
    )
    entry_id = create_response.json()["id"]

    upload_response = await client.post(
        f"/api/v1/financial-entries/{entry_id}/screenshot",
        headers=headers,
        files={"file": ("receipt.png", b"fake-png-bytes", "image/png")},
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["has_screenshot"] is True

    get_response = await client.get(
        f"/api/v1/financial-entries/{entry_id}/screenshot", headers=headers
    )
    assert get_response.status_code == 200
    assert get_response.content == b"fake-png-bytes"

    delete_response = await client.delete(
        f"/api/v1/financial-entries/{entry_id}/screenshot", headers=headers
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["has_screenshot"] is False

    missing_response = await client.get(
        f"/api/v1/financial-entries/{entry_id}/screenshot", headers=headers
    )
    assert missing_response.status_code == 404


@pytest.mark.asyncio
async def test_financial_entry_screenshot_rejects_unsupported_content_type(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    create_response = await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload()
    )
    entry_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/financial-entries/{entry_id}/screenshot",
        headers=headers,
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_financial_entry_screenshot_requires_auth(client: AsyncClient):
    headers = await _register_and_auth_headers(client)
    create_response = await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload()
    )
    entry_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/financial-entries/{entry_id}/screenshot",
        files={"file": ("receipt.png", b"fake-png-bytes", "image/png")},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_financial_entry_screenshot_rejects_oversized_image(client: AsyncClient, monkeypatch):
    headers = await _register_and_auth_headers(client)
    create_response = await client.post(
        "/api/v1/financial-entries", headers=headers, json=_base_entry_payload()
    )
    entry_id = create_response.json()["id"]

    import app.api.v1.financial_entries as financial_entries_module

    monkeypatch.setattr(financial_entries_module, "MAX_UPLOAD_BYTES", 10)

    response = await client.post(
        f"/api/v1/financial-entries/{entry_id}/screenshot",
        headers=headers,
        files={"file": ("receipt.png", b"fake-png-bytes", "image/png")},
    )
    assert response.status_code == 400
