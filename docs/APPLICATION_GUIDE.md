# EdgeLog - How the application works

> Orientation source, not a live-state certificate. Follow [DAILY_SYNC_PROTOCOL.md](DAILY_SYNC_PROTOCOL.md) and the current detailed authorities linked below. Reconcile each claim by its evidence date/revision; do not repeat this guide's unknowns when a newer detailed source has resolved them.


Manual-first trading journal: Plan -> Trade -> Journal -> Reflect -> Improve. Automation can prefill objective candidate data; the trader deliberately confirms and reflects.

Prepare a plan, record/track the trade, journal the outcome, reflect and review analytics. Reconcile completed-trade fees/net P&L against actual execution and statement evidence.

Broker identity, deterministic fill grouping and proposed journal-plan association are distinct stages. A read-only preview is not an import, accepted match, correct P&L or live-execution authorization.

Architecture: FastAPI/Uvicorn, Vue 3/Vite and PostgreSQL/Alembic. Strategy Trader follows Plan -> Validate -> Take Trade -> Track -> Journal/Learn; order origination and TopstepX credentials remain on the personal device. Cloud is not an order relay.

Authorities: [workflow](DEVELOPMENT_WORKFLOW.md), [environment reference](ENVIRONMENT_REFERENCE.md), [data-first slices](DATA_FIRST_VERTICAL_SLICES_2026-10-13.md), [current status](../status.md). Unknown fee semantics and unresolved executions remain unknown.

## Session context

[Daily sync](../DAILY-SYNC.md) | [Development workflow](DEVELOPMENT_WORKFLOW.md) | [Operations runbook](RUNBOOK.md). These guides route to existing authorities; they do not expand scope.