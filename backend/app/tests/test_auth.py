"""Authentication endpoint tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_new_user(client: AsyncClient):
    """Test user registration with valid data."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "securepassword123"}
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" in response.cookies


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test registration with duplicate email fails."""
    # Register first user
    await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )

    # Try to register again with same email
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "different123"}
    )

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test successful login."""
    # Register user
    await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )

    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in response.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test login with wrong password fails."""
    # Register user
    await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "correctpassword"}
    )

    # Try to login with wrong password
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"}
    )

    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with non-existent email fails."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "password123"}
    )

    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_protected_route_requires_token(client: AsyncClient):
    """Test protected route requires authentication."""
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 403  # No token provided


@pytest.mark.asyncio
async def test_protected_route_with_valid_token(client: AsyncClient):
    """Test protected route works with valid token."""
    # Register and get token
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )
    token = register_response.json()["access_token"]

    # Access protected route
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_refresh_token_flow(client: AsyncClient):
    """Test refresh token restores authentication."""
    # Register user (gets refresh cookie)
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )

    # Use refresh endpoint to get new access token
    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_logout_clears_refresh_token(client: AsyncClient):
    """Test logout clears refresh token cookie."""
    # Register user
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )

    # Logout
    response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    # Check that refresh_token cookie is cleared
    cookies = response.cookies
    refresh_cookie = cookies.get("refresh_token")
    assert refresh_cookie is None or refresh_cookie == ""
