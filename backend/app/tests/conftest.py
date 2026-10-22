"""Test configuration and fixtures."""
import uuid

import asyncpg
import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.core.database import Base, get_db

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://edgelog:edgelog_dev_password@localhost/edgelog_test"

# Same local Postgres server/credentials as TEST_DATABASE_URL, used only to
# issue CREATE DATABASE/DROP DATABASE admin commands -- asyncpg is used
# directly here (not SQLAlchemy) because those statements can't run inside
# a transaction block, which SQLAlchemy's asyncpg driver wraps by default.
ADMIN_DSN = "postgresql://edgelog:edgelog_dev_password@localhost/edgelog_test"


@pytest.fixture
async def scratch_database_url() -> AsyncGenerator[str, None]:
    """A freshly created, completely empty Postgres database (no tables,
    no alembic_version) for tests that need to exercise the real Alembic
    migration chain -- the `db_session`/`test_engine` fixtures above use
    Base.metadata.create_all(), which bypasses Alembic entirely and never
    creates an alembic_version table, so they can't be used for this.
    Dropped again after the test, even on failure."""
    db_name = f"edgelog_scratch_{uuid.uuid4().hex[:12]}"

    admin_conn = await asyncpg.connect(ADMIN_DSN)
    try:
        await admin_conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await admin_conn.close()

    try:
        yield f"postgresql+asyncpg://edgelog:edgelog_dev_password@localhost/{db_name}"
    finally:
        admin_conn = await asyncpg.connect(ADMIN_DSN)
        try:
            await admin_conn.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
        finally:
            await admin_conn.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Create a fresh async engine for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop tables and dispose engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with TestSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
