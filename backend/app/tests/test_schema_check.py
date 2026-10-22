"""Regression tests for the issue #57 read-only schema-revision check."""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.migrations import run_pending_migrations
from app.core.schema_check import check_schema_status, expected_head_revision


@pytest.mark.asyncio
async def test_up_to_date_after_real_migration(scratch_database_url, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", scratch_database_url)
    await run_pending_migrations()

    engine = create_async_engine(scratch_database_url)
    try:
        Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with Session() as db:
            status = await check_schema_status(db)
    finally:
        await engine.dispose()

    assert status.up_to_date is True
    assert status.current_revision == expected_head_revision()


@pytest.mark.asyncio
async def test_stale_revision_is_reported_and_check_is_read_only(scratch_database_url, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", scratch_database_url)
    await run_pending_migrations()

    engine = create_async_engine(scratch_database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("UPDATE alembic_version SET version_num = '011'"))

        Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with Session() as db:
            status = await check_schema_status(db)
    finally:
        await engine.dispose()

    assert status.up_to_date is False
    assert status.current_revision == "011"
    assert status.expected_revision == expected_head_revision()

    # The check itself must never write -- the stamped-stale revision
    # should still read back as "011", not have been "fixed" to head.
    engine = create_async_engine(scratch_database_url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            assert result.first()[0] == "011"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_brand_new_database_has_no_current_revision(scratch_database_url, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", scratch_database_url)

    engine = create_async_engine(scratch_database_url)
    try:
        Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with Session() as db:
            status = await check_schema_status(db)
    finally:
        await engine.dispose()

    assert status.up_to_date is False
    assert status.current_revision is None
    assert status.expected_revision == expected_head_revision()
