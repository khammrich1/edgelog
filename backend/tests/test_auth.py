import pytest

pytestmark = pytest.mark.asyncio


async def test_register_login_refresh_logout_flow(client):
    register_response = await client.post(
        "/auth/register", json={"email": "trader@edgelog.trade", "password": "correct-horse-battery"}
    )
    assert register_response.status_code == 201
    body = register_response.json()
    assert body["user"]["email"] == "trader@edgelog.trade"
    assert "access_token" in body
    assert "edgelog_refresh" in register_response.cookies

    duplicate_response = await client.post(
        "/auth/register", json={"email": "trader@edgelog.trade", "password": "another-password"}
    )
    assert duplicate_response.status_code == 409

    login_response = await client.post(
        "/auth/login", json={"email": "trader@edgelog.trade", "password": "correct-horse-battery"}
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    me_response = await client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "trader@edgelog.trade"

    unauthenticated_response = await client.get("/auth/me")
    assert unauthenticated_response.status_code == 401

    refresh_response = await client.post("/auth/refresh")
    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json()

    logout_response = await client.post("/auth/logout")
    assert logout_response.status_code == 204

    post_logout_refresh = await client.post("/auth/refresh")
    assert post_logout_refresh.status_code == 401


async def test_login_rejects_wrong_password(client):
    await client.post("/auth/register", json={"email": "wrong@edgelog.trade", "password": "correct-horse-battery"})

    response = await client.post("/auth/login", json={"email": "wrong@edgelog.trade", "password": "nope"})
    assert response.status_code == 401
