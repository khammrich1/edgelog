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

## Workflow and truthfulness

1. Inspect repo + connected services before making the owner click around.
2. Distinguish **merged**, **auto-deployed to DEV**, **runtime verified**, **owner-tested**, and **PROD verified**.
3. PR merge needs owner approval; PROD deployment needs separate owner approval. Keep broker import write paths blocked until provider-backed account ownership is real.
4. When an owner test fails, investigate and repair the actual environment first; do not ask for the same test repeatedly.
5. Document root causes and update this checklist whenever a repeated mistake exposes a missing operational fact.
