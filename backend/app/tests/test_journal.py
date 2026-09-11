"""Daily Journal endpoint tests (VS2)."""
import pytest
from httpx import AsyncClient


async def _register_and_auth_headers(client: AsyncClient, email: str = "trader@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_journal_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/journal/days/2026-01-05")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_day_auto_creates_it_with_no_checklist(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    response = await client.get("/api/v1/journal/days/2026-01-05", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2026-01-05"
    assert data["status"] == "draft"
    assert data["sleep_quality"] is None
    assert data["mood"] is None
    assert data["has_bias_chart"] is False
    assert data["checklist"] == []


@pytest.mark.asyncio
async def test_update_trading_day_fields(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    response = await client.put(
        "/api/v1/journal/days/2026-01-05",
        headers=headers,
        json={"sleep_quality": 4, "mood": 3, "market_bias": "Bullish above VWAP."},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["sleep_quality"] == 4
    assert data["mood"] == 3
    assert data["market_bias"] == "Bullish above VWAP."


@pytest.mark.asyncio
async def test_checklist_items_appear_on_day_and_can_be_toggled(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    create_response = await client.post(
        "/api/v1/journal/checklist-items", headers=headers, json={"label": "Check economic calendar"}
    )
    assert create_response.status_code == 201
    item_id = create_response.json()["id"]

    day_response = await client.get("/api/v1/journal/days/2026-01-06", headers=headers)
    checklist = day_response.json()["checklist"]
    assert len(checklist) == 1
    assert checklist[0]["checklist_item_id"] == item_id
    assert checklist[0]["label"] == "Check economic calendar"
    assert checklist[0]["completed"] is False

    toggle_response = await client.put(
        f"/api/v1/journal/days/2026-01-06/checklist/{item_id}",
        headers=headers,
        json={"completed": True},
    )
    assert toggle_response.status_code == 200
    assert toggle_response.json()["checklist"][0]["completed"] is True


@pytest.mark.asyncio
async def test_deactivating_checklist_item_preserves_history_but_stops_new_days_getting_it(
    client: AsyncClient,
):
    headers = await _register_and_auth_headers(client)

    create_response = await client.post(
        "/api/v1/journal/checklist-items", headers=headers, json={"label": "Review journal"}
    )
    item_id = create_response.json()["id"]

    # Opens a day while the item is active, and completes it.
    await client.get("/api/v1/journal/days/2026-01-07", headers=headers)
    await client.put(
        "/api/v1/journal/days/2026-01-07/checklist/{}".format(item_id),
        headers=headers,
        json={"completed": True},
    )

    # Deactivate the item.
    delete_response = await client.delete(f"/api/v1/journal/checklist-items/{item_id}", headers=headers)
    assert delete_response.status_code == 204

    # The already-opened day still shows the historical completion.
    old_day_response = await client.get("/api/v1/journal/days/2026-01-07", headers=headers)
    old_checklist = old_day_response.json()["checklist"]
    assert len(old_checklist) == 1
    assert old_checklist[0]["completed"] is True

    # A day opened after deactivation does not get the item.
    new_day_response = await client.get("/api/v1/journal/days/2026-01-08", headers=headers)
    assert new_day_response.json()["checklist"] == []

    # It no longer shows in the active checklist config.
    active_items_response = await client.get("/api/v1/journal/checklist-items", headers=headers)
    assert active_items_response.json() == []


@pytest.mark.asyncio
async def test_locking_a_day_blocks_edits_until_unlocked(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    await client.get("/api/v1/journal/days/2026-01-09", headers=headers)

    lock_response = await client.post("/api/v1/journal/days/2026-01-09/lock", headers=headers)
    assert lock_response.status_code == 200
    assert lock_response.json()["status"] == "locked"

    blocked_response = await client.put(
        "/api/v1/journal/days/2026-01-09", headers=headers, json={"mood": 5}
    )
    assert blocked_response.status_code == 409

    unlock_response = await client.post("/api/v1/journal/days/2026-01-09/unlock", headers=headers)
    assert unlock_response.status_code == 200
    assert unlock_response.json()["status"] == "draft"

    allowed_response = await client.put(
        "/api/v1/journal/days/2026-01-09", headers=headers, json={"mood": 5}
    )
    assert allowed_response.status_code == 200
    assert allowed_response.json()["mood"] == 5


@pytest.mark.asyncio
async def test_bias_chart_upload_get_and_delete(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    upload_response = await client.post(
        "/api/v1/journal/days/2026-01-10/bias-chart",
        headers=headers,
        files={"file": ("chart.png", b"fake-png-bytes", "image/png")},
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["has_bias_chart"] is True

    get_response = await client.get("/api/v1/journal/days/2026-01-10/bias-chart", headers=headers)
    assert get_response.status_code == 200
    assert get_response.content == b"fake-png-bytes"

    delete_response = await client.delete("/api/v1/journal/days/2026-01-10/bias-chart", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["has_bias_chart"] is False

    missing_response = await client.get("/api/v1/journal/days/2026-01-10/bias-chart", headers=headers)
    assert missing_response.status_code == 404


@pytest.mark.asyncio
async def test_bias_chart_rejects_unsupported_content_type(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    response = await client.post(
        "/api/v1/journal/days/2026-01-11/bias-chart",
        headers=headers,
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_trading_days_returns_summaries_in_range(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    await client.post("/api/v1/journal/checklist-items", headers=headers, json={"label": "Warm up"})
    await client.get("/api/v1/journal/days/2026-01-05", headers=headers)
    await client.get("/api/v1/journal/days/2026-01-20", headers=headers)  # outside the query range below

    response = await client.get(
        "/api/v1/journal/days", headers=headers, params={"start": "2026-01-01", "end": "2026-01-10"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-01-05"
    assert data[0]["checklist_total_count"] == 1
    assert data[0]["checklist_completed_count"] == 0


@pytest.mark.asyncio
async def test_list_trading_days_rejects_inverted_range(client: AsyncClient):
    headers = await _register_and_auth_headers(client)

    response = await client.get(
        "/api/v1/journal/days", headers=headers, params={"start": "2026-01-10", "end": "2026-01-01"}
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_checklist_items_are_scoped_per_user(client: AsyncClient):
    headers_a = await _register_and_auth_headers(client, email="trader-a@example.com")
    headers_b = await _register_and_auth_headers(client, email="trader-b@example.com")

    create_response = await client.post(
        "/api/v1/journal/checklist-items", headers=headers_a, json={"label": "Trader A only"}
    )
    item_id = create_response.json()["id"]

    other_users_view = await client.get("/api/v1/journal/checklist-items", headers=headers_b)
    assert other_users_view.json() == []

    forbidden_update = await client.put(
        f"/api/v1/journal/checklist-items/{item_id}", headers=headers_b, json={"label": "hijacked"}
    )
    assert forbidden_update.status_code == 404
