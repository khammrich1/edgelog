# EdgeLog: check these before troubleshooting or instructing the owner

**Mandatory operational preflight.** Read this document and [ENVIRONMENT_REFERENCE.md](ENVIRONMENT_REFERENCE.md) before giving any EdgeLog deployment, API-test, migration, auth, or broker-integration instructions. Check live evidence; this document records facts observed on 2026-10-20, not an excuse to assume future state.

## Connections and environments — don't guess

- **GitHub:** `khammrich1/edgelog`. Read `AGENTS.md`, workflow docs, actual code, PRs, and migrations first. Do not call a PR deployed merely because it merged; public DEV auto-deploys from `main` but must be checked.
- **Public DEV:** `https://d.edgelog.trade`, **DigitalOcean App Platform**, auto-deploy from `main`. App `edgelog-dev`, backend component `edgelog-backend`. Its database is the **connected Supabase project `edgelog-dev`**, project ID `irkoyygprvwnjbvauodk`, under the Supabase linked account named **Edglelog**. The Supabase connector is available in ChatGPT: **check it before telling the owner to open a terminal or migrate manually**.
- **PROD:** `https://edgelog.trade`, DigitalOcean droplet, owner-authorized `el-deploy` only. Do **not** assume it uses the DEV Supabase project. Never point DEV migrations at PROD.
- The droplet also hosts a *local* DEV checkout and service; **that is not public DEV**. Do not run `dev-el-deploy` expecting it to update public DEV.
- **Available access:** GitHub connector and Supabase connector. Check connected tools and project identities **before** claiming access is unavailable, proposing Work mode, or asking the owner to run commands. No DigitalOcean shell connector was available in this chat on 2026-10-20.

## Authentication and API tests — inspect implementation first

- Vue/Pinia access token lives **in memory** (`frontend/src/stores/auth.js`), **not localStorage**. Axios attaches Bearer token (`frontend/src/services/api.js`). Backend requires Bearer auth (`backend/app/api/deps.py`).
- HttpOnly refresh cookie supports `POST /api/v1/auth/refresh`, which returns a new access token for authenticated DEV browser tests. Never ask the owner to reveal credentials, access tokens, or cookie values.
- FastAPI's default OpenAPI URL is **`/openapi.json`**, not `/api/v1/openapi.json`; the API router prefix is `/api/v1` (`backend/app/main.py`). Confirm ingress behavior rather than guessing.
- `GET /api/v1/broker-accounts` returning `{"detail":"Not authenticated"}` unauthenticated means the route is registered and auth is enforced. HTTP 500 after auth is a backend/database failure: inspect logs and migration state, not browser storage.

## Migrations — check database before blaming deployment

- Public DEV's Supabase `edgelog-dev` database was found at **Alembic 011** after PR #98 merged, causing authenticated GET/POST `/api/v1/broker-accounts` to return HTTP 500.
- On **2026-10-20**, the Supabase connector applied the equivalent of additive Alembic revision **012** to DEV only: `public.broker_accounts` table, indexes, and `public.alembic_version` updated to `012`. Verified table exists and initially contained **zero** records. **PROD untouched.**
- Before any migration: verify project name/ID, database identity, current `alembic_version`, existing table/columns, migration code and revision chain. Do not reapply revision 012 blindly. Prefer the application's normal Alembic deployment path when available; direct Supabase SQL is an exceptional repair and must preserve the Alembic revision state. Never modify historical trade records without explicit approval.
- **Outstanding:** confirm automated migrations run for future public DEV App Platform deployments; GitHub merge/healthy deployment does not imply DB schema upgraded. After schema repair, rerun authenticated create/duplicate/list/delete tests and record owner acceptance.

### 2026-10-21 — Issue #57: automated migrations on every backend startup

**Root cause**, confirmed by repo inspection: there is **no `.do/app.yaml`, Procfile, Dockerfile, or release-command config anywhere in this repository** — the App Platform build/run spec lives only in DO's dashboard, not version control, and it apparently never included a migration step. So every deploy to public DEV restarts `edgelog-backend` against whatever schema the Supabase `edgelog-dev` database already has, with nothing in the deploy lifecycle running `alembic upgrade head`. PR #98 (migration 012, `broker_accounts`) merged and auto-deployed cleanly while the DB stayed at 011, producing the HTTP 500s above. This is the second occurrence of this exact failure class (the first: issue #90).

**Fix** (`backend/app/core/migrations.py`, `backend/app/core/schema_check.py`, `backend/app/main.py` — see that issue's PR): the backend now migrates itself on every startup, using the same `settings.DATABASE_URL` it already connects with, so there is no DigitalOcean dashboard config to get wrong and no separate "which database" question:
- **Startup hook** (`app.main`'s `lifespan`) awaits `run_pending_migrations()` before the app finishes starting. It runs `alembic upgrade head` (a no-op if already current) under a Postgres session-level advisory lock, so concurrent instances/workers starting at once serialize instead of racing. It is **unguarded** — if it raises, startup fails and the ASGI server never reports ready, so App Platform's health-gated rollout never cuts traffic to that instance.
- **`/health`** independently re-verifies on every call (`app.core.schema_check`): compares the DB's recorded `alembic_version` against the code's own Alembic head (read from the migration scripts on disk, not the DB) and returns HTTP 503 `{"reason": "schema_mismatch", "current_revision": ..., "expected_revision": ...}` — or `"database_unreachable"` on a connectivity failure — instead of a false 200. It never writes to the database itself; a stale revision stays stale until the startup hook (or a manual migration) actually fixes it.
- Both layers are independent and intentionally redundant: a deploy mechanism that skips Python startup hooks entirely would still be caught by `/health`; a health check App Platform doesn't poll would still be caught by the startup failure.

**Tests added** (local scratch-database fixtures only — a freshly `CREATE DATABASE`'d, genuinely empty Postgres DB per test, dropped after; **never** the real DEV Supabase project, and migration 012 is **not** re-run against it): `backend/app/tests/test_startup_migrations.py` (fresh-DB-to-head upgrade with table spot-checks, idempotency, concurrent-startup race safety via two simultaneous calls), `backend/app/tests/test_schema_check.py` (up-to-date, stale-revision-detected-and-read-only, brand-new-DB-with-no-tables), `backend/app/tests/test_health_endpoint.py` (unmigrated DB → 503, migrated DB → 200, stale DB → repeated 503s that never self-heal).

**DEV acceptance, once this PR is merged and deployed** (no code path here touches PROD or re-applies 012 to the real DEV DB; this only changes what happens automatically on the *next* deploy):
1. After the next public-DEV deploy, check App Platform's runtime logs for `edgelog-backend` for `app.migrations.upgrade_starting` / `app.migrations.upgrade_complete` (or a startup failure, which is also a valid finding — it means a real migration problem is being correctly caught before traffic is served).
2. `curl https://d.edgelog.trade/health` (or the backend's direct App Platform URL) and confirm `{"status": "healthy", "service": "edgelog-api"}`.
3. Independently confirm DEV's actual Alembic revision matches this code's head — via the Supabase connector (`SELECT version_num FROM alembic_version;` against the `edgelog-dev` project) or `alembic current`/`alembic heads` run against DEV's `DATABASE_URL` — rather than trusting `/health` alone.
4. Re-run the authenticated `/api/v1/broker-accounts` create/duplicate/list/delete tests from the issue #95/#98 verification to confirm the endpoint that originally broke now behaves correctly end-to-end.

## Workflow and truthfulness

1. Inspect repo + connected services before making the owner click around.
2. Distinguish **merged**, **auto-deployed to DEV**, **runtime verified**, **owner-tested**, and **PROD verified**.
3. PR merge needs owner approval; PROD deployment needs separate owner approval. Keep broker import write paths blocked until provider-backed account ownership is real.
4. When an owner test fails, investigate and repair the actual environment first; do not ask for the same test repeatedly.
5. Document root causes and update this checklist whenever a repeated mistake exposes a missing operational fact.
