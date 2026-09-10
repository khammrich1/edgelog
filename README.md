# EdgeLog

**Trade. Reflect. Improve.**

EdgeLog is a manual-first trading journal built to help traders document their process, review execution, understand behavioral patterns, and identify their actual trading edge.

- Domain: `edgelog.trade`
- Owner: Green Bread Enterprises LLC
- Operating line: Green Bread Trades
- Development model: vertical slices, one accepted slice at a time

## Product principles

- Manual entry is the primary workflow.
- Journaling should be fast, deliberate, and comfortable enough for daily use.
- Analytics and AI support reflection; they are not the product's identity.
- EdgeLog is not a broker, signal service, trading bot, or automated-import-first platform.
- Psychology features may use structured cognitive-behavioral reflection techniques, but EdgeLog is not therapy or a mental-health treatment product.

## Current status

**VS1 — Foundation** is the current authorized build.

See [EDGELOG.md](EDGELOG.md) for the product specification and [ROADMAP.md](ROADMAP.md) for vertical slices.

## Project layout

- `backend/` — FastAPI + SQLAlchemy (async) + Alembic + PostgreSQL, Argon2/JWT auth
- `frontend/` — Vue 3 + Vite + Pinia + Vue Router, CSS design tokens

## Running locally

### Database

```
docker compose up -d
```

### Backend

```
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Run tests with `pytest` from `backend/`.

### Frontend

```
cd frontend
npm install
npm run dev
```

Vite proxies `/api/*` to `http://localhost:8000` in development. Production build: `npm run build`.
