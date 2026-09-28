# Claude Open-Issue Work Queue

This file establishes the current owner-authorized coordination queue for EdgeLog. Individual GitHub issues remain the source of truth for scope and acceptance criteria.

Convention: an **issue** is a backlog item/specification. A **PR** is the actual implementation/testable unit for one or more issues. An issue with no linked PR yet has not been started.

## Active queue (Strategy Trader epic)

- #25 — Strategy Trader ST0: Local TopstepX execution foundation -- **built, in PR #31**, stopped for owner acceptance testing before #26 begins
- #26 — Strategy Trader ST1: Practice limit-order execution and kill controls -- blocked on #25 acceptance
- #27 — Strategy Trader ST2: Strategy contract and observe-only engine -- blocked on #26
- #28 — Strategy Trader ST3: Risk engine and Practice auto-execution -- blocked on #27
- #29 — Strategy Trader ST4: EdgeLog strategy control panel and automatic journaling -- blocked on #28
- #30 — Strategy analytics: win rate and per-day performance stats -- deliberately deferred until #29/ST4 lands canonical strategy ID/version/source + execution metadata

### Strategy Trader dependency order

Work #25 → #26 → #27 → #28 → #29 in dependency order. Do not begin the next issue in this chain until the owner has explicitly accepted the one before it. Strategy analytics #30 must be anticipated by ST4's canonical trade metadata and implemented once automated trade reconciliation is stable.

## Backlog (scoped, not currently in the active queue)

These are legitimate future specifications, not superseded or abandoned -- they simply aren't being worked right now and have no sequencing dependency on the Strategy Trader epic above.

- #4 — Future slice: Mentorship groups and daily check-in dashboard
- #5 — Future slice: Required pre-trade daily check-in for mentorship members
- #6 — Future slice: Mentor mentee detail view with check-ins and trades
- #32 — Trade Ranker: personal A+ setup grading (setups, confluences, versioning, AI-assisted) -- see `ROADMAP.md` VS4.9. Does not block, and is not blocked by, the Strategy Trader epic; connects to #30's analytics scope once both exist.

## Closed

- #8 — VS2: Daily Journal Core -- closed 2026-09-28, already implemented and accepted via PR #7 (merged 2026-09-11).

## Delivery rules

- Read and reference the individual issue before implementation.
- Keep implementation traceable to its issue.
- Use canonical EdgeLog Trading Day / Trade / TradeEntry / TradeExit data rather than parallel stores.
- Web changes go to d.edgelog.trade for owner testing.
- No production deployment or major milestone merge without owner acceptance.
- Keep Topstep credentials local; never commit, log, or store them in EdgeLog cloud.
- Topstep trading/order origination stays on the trader's personal device as scoped by Strategy Trader issues.
- Keep accepted documentation synchronized with implemented behavior.
