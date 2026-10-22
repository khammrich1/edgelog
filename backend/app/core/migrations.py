"""Startup-time migration runner (issue #57 follow-up, 2026-10-21).

Root cause this exists to close: PR #98 merged and auto-deployed to
public DEV via DigitalOcean App Platform, but nothing in the deploy
lifecycle ever ran `alembic upgrade head` against DEV's database --
App Platform has no checked-in build/run spec in this repo (no
`.do/app.yaml`, no release command, no Procfile), and its actual
dashboard configuration apparently never included one either. The new
backend code (expecting migration 012's `broker_accounts` table) began
serving requests against a database still at revision 011, producing
authenticated HTTP 500s until someone manually repaired DEV's schema
through the Supabase connector -- see docs/OPERATIONS_PREFLIGHT.md.

Fix: make the application itself responsible for bringing its own
database to the code's expected head, every time it starts, rather than
depending on an out-of-repo platform step that may or may not exist.
This needs no DigitalOcean dashboard configuration at all -- it runs
inside `app.main`'s FastAPI startup hook, using the exact same
`settings.DATABASE_URL` the app already connects with, so there is no
separate "which database" question to get wrong.

Fail-closed: `run_pending_migrations()` is awaited directly from the
startup event, with nothing catching what it raises. A FastAPI/Starlette
startup handler that raises stops the application from finishing
startup -- the ASGI server never reports ready, so DigitalOcean App
Platform's own health-check-gated rollout never cuts traffic to an
instance whose migration failed. This is in addition to, not instead
of, app.core.schema_check's live /health verification.

Idempotent and safe under concurrent startup: `alembic upgrade head` is
already a no-op when the database is already at head, and the Postgres
session-level advisory lock held for the duration of the upgrade means
two instances (or workers) starting at the same moment serialize rather
than race -- the second simply waits for the first to finish, then finds
there is nothing left to do.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

logger = logging.getLogger("app.migrations")

# Arbitrary fixed 64-bit key for the Postgres advisory lock guarding
# migrations. Any constant works as long as nothing else in this
# codebase reuses it for an unrelated lock -- nothing else does today.
MIGRATION_LOCK_KEY = 557_701_912_001

BACKEND_DIR = Path(__file__).resolve().parents[2]
ALEMBIC_INI_PATH = BACKEND_DIR / "alembic.ini"
ALEMBIC_SCRIPT_LOCATION = BACKEND_DIR / "alembic"


def build_alembic_config() -> Config:
    """The same alembic.ini this backend ships, with script_location
    resolved to an absolute path so this works regardless of the
    process's current working directory (uvicorn's included)."""
    cfg = Config(str(ALEMBIC_INI_PATH))
    cfg.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))
    return cfg


async def run_pending_migrations() -> None:
    """Upgrades the connected database to the code's Alembic head.
    Never logs DATABASE_URL or any other secret -- only revision IDs,
    which are not sensitive."""
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as lock_connection:
            await lock_connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": MIGRATION_LOCK_KEY})
            try:
                logger.info("app.migrations.upgrade_starting")
                # alembic.command.upgrade is synchronous and internally
                # calls asyncio.run() (see alembic/env.py) -- running it
                # directly here would collide with the event loop this
                # startup hook is already running in. asyncio.to_thread
                # gives it a fresh thread (and therefore a fresh event
                # loop for its own asyncio.run() call) instead.
                await asyncio.to_thread(command.upgrade, build_alembic_config(), "head")
                logger.info("app.migrations.upgrade_complete")
            finally:
                await lock_connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK_KEY})
    finally:
        await engine.dispose()
