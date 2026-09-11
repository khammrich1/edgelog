"""CORS configuration regression tests.

Guards against a config change that (re)introduces a wildcard/reflect-all
origin policy. The frontend and API are served from the same origin in
production, so the browser's own requests never need CORS approval at all;
these headers only matter for a genuinely cross-origin caller, and only an
explicitly allow-listed one should ever get them.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_allowed_origin_is_echoed_back(client: AsyncClient):
    response = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


@pytest.mark.asyncio
async def test_disallowed_origin_is_not_echoed_back(client: AsyncClient):
    response = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_cors_is_never_configured_as_wildcard():
    from app.main import app

    for middleware in app.user_middleware:
        if middleware.cls.__name__ == "CORSMiddleware":
            assert "*" not in middleware.kwargs.get("allow_origins", [])
            return

    pytest.fail("CORSMiddleware is not configured on the app")
