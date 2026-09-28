# Claude Open-Issue Work Queue

This file establishes the current owner-authorized coordination queue for EdgeLog. Individual GitHub issues remain the source of truth for scope and acceptance criteria.

## Open issues

- #4 — Future slice: Mentorship groups and daily check-in dashboard
- #5 — Future slice: Required pre-trade daily check-in for mentorship members
- #6 — Future slice: Mentor mentee detail view with check-ins and trades
- #8 — VS2: Daily Journal Core
- #25 — Strategy Trader ST0: Local TopstepX execution foundation
- #26 — Strategy Trader ST1: Practice limit-order execution and kill controls
- #27 — Strategy Trader ST2: Strategy contract and observe-only engine
- #28 — Strategy Trader ST3: Risk engine and Practice auto-execution
- #29 — Strategy Trader ST4: EdgeLog strategy control panel and automatic journaling
- #30 — Strategy analytics: win rate and per-day performance stats

## Strategy Trader dependency order

Work #25 → #26 → #27 → #28 → #29 in dependency order. Strategy analytics #30 must be anticipated by ST4's canonical trade metadata and implemented once automated trade reconciliation is stable.

## Delivery rules

- Read and reference the individual issue before implementation.
- Keep implementation traceable to its issue.
- Use canonical EdgeLog Trading Day / Trade / TradeEntry / TradeExit data rather than parallel stores.
- Web changes go to d.edgelog.trade for owner testing.
- No production deployment or major milestone merge without owner acceptance.
- Keep Topstep credentials local; never commit, log, or store them in EdgeLog cloud.
- Topstep trading/order origination stays on the trader's personal device as scoped by Strategy Trader issues.
- Keep accepted documentation synchronized with implemented behavior.
