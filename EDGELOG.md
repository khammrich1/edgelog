# EdgeLog Product Specification

## Identity

**EdgeLog** is a new standalone product, built from scratch.

- Domain: `edgelog.trade`
- Owner: Green Bread Enterprises LLC
- Operating line: Green Bread Trades
- Core loop: **TRADE → REFLECT → IMPROVE**
- Primary brand phrase: **Find Your Edge.**

The existing Profit Pros / TradeJournal application is a reference only. EdgeLog does not inherit its codebase, database schema, UI, or technical debt by default.

## Product positioning

EdgeLog is a trading journal centered on **intentional manual entry**. Traders record preparation, market bias, trades, execution, psychology, mistakes, discipline, reflections, and results.

Over time, EdgeLog should help answer:

- What setups actually work?
- Where do losses come from?
- What conditions produce the best trading?
- How does psychology affect performance?
- Is the trader following their own process?
- Where does the trader's actual statistical edge exist?

EdgeLog is not primarily an automated trade importer, broker, signal service, trading bot, AI trading platform, or social network.

## Product philosophy

Journaling must be easy enough to use every trading day.

Manual entry should be:

- fast
- comfortable
- uncluttered
- deliberate
- easy to understand
- optimized for repeated daily use

Every field should earn its place by helping the trader:

1. document what happened
2. evaluate execution
3. identify behavioral patterns
4. discover their edge

Psychology features may use structured techniques inspired by cognitive behavioral therapy (CBT), such as identifying thoughts, emotional triggers, cognitive distortions, urges, chosen actions, and outcomes. EdgeLog should present these as self-reflection and performance-journaling tools, not as therapy, diagnosis, or mental-health treatment.

## Visual identity

EdgeLog uses a dark, professional visual system:

- **Copper** — primary brand/accent, starting at `#B87333`
- **Onyx** — primary background, starting at `#0D0D0D`
- **Graphite** — primary surfaces, starting at `#2B2B2B`
- **Steel** — muted text, borders, and secondary UI, starting at `#6B6B6B`
- **Off-white** — primary text, approximately `#F5F5F5`

Functional colors remain separate from brand colors:

- green = positive/profit
- red = negative/loss
- neutral gray = no result / no trade
- copper = EdgeLog identity, action, selection, and emphasis

### Design character

EdgeLog should feel precise, calm, disciplined, serious, modern, tactile, premium, and data-aware.

Preferred direction: **professional field instrument + premium journal**.

Avoid neon UI, excessive glow, excessive gradients, crypto aesthetics, bulls/bears, money graphics, Wall Street clichés, giant decorative cards, and unnecessary animation.

### Key UI reference

A primary design reference for the app is a dark weekly trading-calendar interface with:

- near-black / onyx background
- narrow icon-focused left navigation rail
- condensed uppercase typography
- thin steel grid lines and dividers
- graphite trade cards
- restrained copper highlights
- dense but readable information layout
- selected trade cards expanding in context instead of forcing unnecessary navigation

This visual language should influence the broader EdgeLog application, not only the Trade Calendar.

## Logo direction

Use a geometric **E** built from layered/angular elements.

The logo should:

- use copper + steel
- have a strong silhouette
- work as a favicon and small application mark
- work beside the EdgeLog wordmark
- feel modern, slightly industrial, and instrument-like
- suggest an edge emerging from structured information

Avoid candlesticks, bulls, bears, dollar signs, airplanes, notebooks, generic charts, and crypto-exchange styling.

## Typography

Use a clean modern sans-serif for primary UI. A restrained monospace may be used selectively for prices, P&L, R values, timestamps, and statistics.

Examples that must remain highly readable:

- `MNQ`
- `24,518.25`
- `+$327.50`
- `+2.15R`
- `07:42`

## Development model

EdgeLog is built using vertical slices.

Rules:

- Build one slice at a time.
- Do not implement future slices early.
- Do not create speculative infrastructure without a current need.
- Do not create fake placeholder versions of future features.
- Each slice must create a usable, testable improvement.
- Tests and production build must pass before acceptance.
- Manual testing is required before a slice is accepted.
- Do not begin the next slice until the current slice is accepted.

## Current authorized work

**VS1 — Foundation is accepted.** **VS2 — Daily Journal Core** is the current authorized work.

No VS3+ functionality should be implemented until VS2 is tested and accepted.

## VS1 technical direction

Approved direction:

### Frontend

- Vue 3
- Vite
- Pinia
- Vue Router
- CSS design tokens; no unnecessary UI framework
- current stable compatible dependency versions

### Backend

- FastAPI
- PostgreSQL
- SQLAlchemy 2.x async
- asyncpg
- Alembic
- Argon2 password hashing
- JWT access tokens
- secure refresh-session flow

### Authentication

- short-lived access token, approximately 15 minutes
- access token preferably kept in application memory
- refresh token in an HttpOnly cookie
- Secure cookie in production
- SameSite configured appropriately for deployment architecture
- authentication restored after refresh via refresh/session endpoint
- logout clears/invalidates refresh session
- no long-lived auth credentials in localStorage

### VS1 data model

Keep the schema minimal.

Required user data:

- id
- email
- password_hash
- created_at
- updated_at

A minimal auth/session table is allowed if required for secure refresh-token rotation or logout invalidation.

Do not pre-create trade, trading-day, journal, psychology, analytics, XP, education, or social tables.

### VS1 acceptance

VS1 is accepted only when:

- EdgeLog runs as its own application
- branding and design tokens are established
- SVG mark works
- registration works
- login works
- logout works
- authentication persists correctly across refresh
- protected routes work
- application shell works
- desktop and mobile layouts work
- production build succeeds
- automated tests pass
- there are no obvious runtime/console errors
- no unnecessary VS2+ functionality exists
