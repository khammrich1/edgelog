# EdgeLog

**Trade. Reflect. Improve.**

EdgeLog is a manual-first trading journal built to help traders document their process, review execution, understand behavioral patterns, and identify their actual trading edge.

- Domain: `edgelog.trade`
- Owner: Green Bread Enterprises LLC
- Operating line: Green Bread Trades
- Development model: owner-test-gated vertical slices

## Product doctrine

**You traded it. You journal it. You own it.**

EdgeLog deliberately preserves the act of journaling. It is not trying to remove the work of reviewing a trade through broker imports and passive analytics. The trader should revisit the setup, plan, execution, outcome, psychology, mistakes, and lessons.

- Manual journaling is the primary workflow and part of the discipline EdgeLog is designed to reinforce.
- EdgeLog should make journaling fast and intelligent without making it passive.
- AI may extract or suggest candidate data, but the trader reviews and confirms it.
- Future execution integrations may prefill objective execution facts, but must not silently complete the journal or reflection process.
- Analytics support reflection and edge discovery; they do not replace the trader's deliberate review.
- EdgeLog is not a broker, signal service, trading bot, or automated-import-first platform.
- Psychology features may use structured cognitive-behavioral reflection techniques, but EdgeLog is not therapy or a mental-health treatment product.

Core process: **Plan → Trade → Journal → Reflect → Improve**.

## Current product-foundation status

- **P1 — Product shell & visual system:** accepted / merged.
- **P2 — Dashboard / first impression:** accepted / merged.
- **P3 — Daily Journal & trade workflow UX:** current owner gate in PR #40; functional behavior has passed, with the latest layout direction accepted enough to stop page-specific visual churn.
- **Next:** P3.5 — a cross-product visual-system/workspace rebuild before onboarding. It must improve depth and hierarchy consistently across Dashboard, Journal, Calendar, Trades, Stats, and future Trade Ranker surfaces rather than redesigning one page in isolation.
- **Strategy Trader:** parked, not abandoned, while the customer-facing product foundation is completed.

See `EDGELOG.md` for product doctrine/identity, `ROADMAP.md` for feature direction, `docs/CLAUDE_WORK_QUEUE.md` for current implementation sequencing, and `docs/DEVELOPMENT_WORKFLOW.md` for the owner-gated delivery process.

## Tech stack

- **Frontend:** Vue 3, Pinia, Vite
- **Backend:** FastAPI, PostgreSQL, SQLAlchemy 2.x
- **Auth:** JWT with HttpOnly refresh cookies

## Development

See `DEVELOPMENT.md` for setup instructions.

## Production

See `DEPLOYMENT.md` for production deployment.

---

**EdgeLog** is a product of **Green Bread Enterprises LLC**, operated under **Green Bread Trades**.
