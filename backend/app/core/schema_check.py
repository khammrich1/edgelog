"""Runtime schema-revision check (issue #57 follow-up).

Backs up app.core.migrations' startup-time upgrade: if this running
instance's database is ever NOT at the code's expected Alembic head --
whatever the reason, including one this specific fix didn't anticipate
-- `/health` must report unhealthy rather than silently serving
requests against an incompatible schema. Read-only: nothing here ever
runs a migration; see app.core.migrations for that.
"""
from __future__ import annotations

from typing import NamedTuple, Optional

from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.migrations import build_alembic_config


def expected_head_revision() -> Optional[str]:
    """The single Alembic head revision this running code expects, read
    straight from the migration scripts on disk -- not from the
    database."""
    script = ScriptDirectory.from_config(build_alembic_config())
    return script.get_current_head()


async def current_db_revision(db: AsyncSession) -> Optional[str]:
    """The database's own recorded revision, or None if the
    `alembic_version` table doesn't exist/is empty (a brand-new,
    never-migrated database). A genuine connectivity failure is
    deliberately NOT caught here -- it propagates to the caller, which
    reports it as "database unreachable", not a schema mismatch."""
    try:
        result = await db.execute(text("SELECT version_num FROM alembic_version"))
    except ProgrammingError:
        await db.rollback()
        return None
    row = result.first()
    return row[0] if row else None


class SchemaStatus(NamedTuple):
    up_to_date: bool
    current_revision: Optional[str]
    expected_revision: Optional[str]


async def check_schema_status(db: AsyncSession) -> SchemaStatus:
    expected = expected_head_revision()
    current = await current_db_revision(db)
    return SchemaStatus(up_to_date=current == expected, current_revision=current, expected_revision=expected)
