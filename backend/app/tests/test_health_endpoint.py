"""Regression tests for the issue #57 fail-closed /health endpoint."""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.core.migrations import run_pending_migrations
from app.core.schema_check import expected_head_revision
from app.main import app


@pytest.mark.asyncio
async def test_health_reports_unhealthy_against_unmigrated_schema(client: AsyncClient):
    """The standard `client` fixture's database is built with
    Base.metadata.create_all(), which never runs Alembic -- whatever
    alembic_version ends up containing (absent, or stale from a prior
    local stamp), it cannot be this code's actual head, so /health must
    treat it as a schema mismatch, not a crash."""
    response = await client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unhealthy"
    assert body["reason"] == "schema_mismatch"
    assert body["current_revision"] != expected_head_revision()
    assert body["expected_revision"] == expected_head_revision()


@pytest.mark.asyncio
async def test_health_reports_healthy_once_migrated_to_head(scratch_database_url, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", scratch_database_url)
    await run_pending_migrations()

    engine = create_async_engine(scratch_database_url)
    try:
        Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async def override_get_db():
            async with Session() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get("/health")
        finally:
            app.dependency_overrides.clear()
    finally:
        await engine.dispose()

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "edgelog-api"}


@pytest.mark.asyncio
async def test_health_never_self_heals_a_stale_schema(scratch_database_url, monkeypatch):
    """/health must only ever report; it must never itself bring the
    database up to date -- repeated calls against a stale DB should keep
    reporting the same stale revision, not drift towards head."""
    monkeypatch.setattr(settings, "DATABASE_URL", scratch_database_url)
    await run_pending_migrations()

    engine = create_async_engine(scratch_database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("UPDATE alembic_version SET version_num = '011'"))

        Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async def override_get_db():
            async with Session() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                first = await ac.get("/health")
                second = await ac.get("/health")
        finally:
            app.dependency_overrides.clear()
    finally:
        await engine.dispose()

    for response in (first, second):
        assert response.status_code == 503
        body = response.json()
        assert body["reason"] == "schema_mismatch"
        assert body["current_revision"] == "011"
