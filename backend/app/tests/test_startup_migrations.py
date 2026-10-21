"""Regression tests for the issue #57 startup migration runner.

These exercise the real Alembic migration chain against a genuinely
fresh, empty Postgres database (via the `scratch_database_url` fixture)
-- unlike the `db_session`/`test_engine` fixtures used elsewhere, which
build tables with Base.metadata.create_all() and never touch Alembic or
alembic_version at all.
"""
import asyncio

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.migrations import run_pending_migrations
from app.core.schema_check import expected_head_revision


async def _current_revision(database_url: str) -> str | None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            try:
                result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            except Exception:
                return None
            row = result.first()
            return row[0] if row else None
    finally:
        await engine.dispose()


async def _table_names(database_url: str) -> set[str]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            return set(await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names()))
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_run_pending_migrations_upgrades_fresh_database_to_head(scratch_database_url, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", scratch_database_url)

    assert await _current_revision(scratch_database_url) is None

    await run_pending_migrations()

    assert await _current_revision(scratch_database_url) == expected_head_revision()
    tables = await _table_names(scratch_database_url)
    assert "users" in tables
    assert "broker_accounts" in tables


@pytest.mark.asyncio
async def test_run_pending_migrations_is_idempotent(scratch_database_url, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", scratch_database_url)

    await run_pending_migrations()
    first_revision = await _current_revision(scratch_database_url)

    await run_pending_migrations()
    second_revision = await _current_revision(scratch_database_url)

    assert first_revision == second_revision == expected_head_revision()


@pytest.mark.asyncio
async def test_run_pending_migrations_serializes_concurrent_startups(scratch_database_url, monkeypatch):
    """Two instances starting at the same moment against the same fresh
    database must not race -- the advisory lock should make the second
    wait for the first, then find nothing left to do, rather than both
    running `alembic upgrade head` against the same schema at once."""
    monkeypatch.setattr(settings, "DATABASE_URL", scratch_database_url)

    results = await asyncio.gather(
        run_pending_migrations(),
        run_pending_migrations(),
        return_exceptions=True,
    )

    for result in results:
        if isinstance(result, Exception):
            raise result

    assert await _current_revision(scratch_database_url) == expected_head_revision()
