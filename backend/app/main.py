"""EdgeLog FastAPI application."""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.migrations import run_pending_migrations
from app.core.schema_check import check_schema_status
from app.api.v1 import api_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Issue #57 follow-up: bring the connected database to this code's
    Alembic head before accepting any traffic. Deliberately unguarded --
    if run_pending_migrations() raises, this context manager propagates
    it, which stops the application from finishing startup (see
    app.core.migrations). Never invoked by the test suite: httpx's
    ASGITransport sends only `http` scopes, never `lifespan`, so pytest
    never triggers this."""
    await run_pending_migrations()
    yield


# Create FastAPI app
app = FastAPI(
    title="EdgeLog API",
    description="Find Your Edge - Trading Journal API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint. Reports unhealthy (503), not a false 200,
    when the database is unreachable or not at this code's expected
    Alembic revision -- see app.core.schema_check. This is what lets
    DigitalOcean App Platform's own health-gated rollout refuse to cut
    traffic to an instance whose schema isn't actually ready, on top of
    the startup-time migration step failing closed on its own."""
    try:
        status = await check_schema_status(db)
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "service": "edgelog-api", "reason": "database_unreachable"},
        )

    if not status.up_to_date:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "edgelog-api",
                "reason": "schema_mismatch",
                "current_revision": status.current_revision,
                "expected_revision": status.expected_revision,
            },
        )

    return {"status": "healthy", "service": "edgelog-api"}
