# EdgeLog — Product Vision, Strategy Validation, Practice Execution & Deployment Priority
**Owner direction recorded: October 8, 2026.** Product specification and roadmap; **not a statement of shipped functionality or approval for live trading**.

## One product
EdgeLog is **one integrated product** (working name; final brand undecided), not a separate web journal and separately marketed Strategy Trader. It is a system for **developing and validating the trader's defined strategies based on their journal and objectively recorded trading data**, then planning, authorizing, locally executing and learning from trades with minimal discretionary interference.

Principle: **The trader defines the hypothesis. EdgeLog tests the evidence. The data earns an A+ designation.**
- A trader's *claimed A+ setup* is a hypothesis, not a validated edge.
- **Setup match** = opportunity satisfies a versioned rule/confluence definition. **Strategy validation** = independent evidence of repeatable performance, with sample size, uncertainty, costs and market regimes. **Execution discipline** = actual adherence to the frozen plan. Keep all three separate.
- An A+ candidate can lose. A winning off-plan trade is still a process violation; a losing plan-adherent trade need not be.
- Do not present confluence count alone as evidence-based A+; the current #32 confluence-count A+ grade is a **user-defined checklist grade**, not a statistically validated designation. Product must label them distinctly and evolve #32 without rewriting historical grades.
- Journal-based data alone is subject to selection bias (only trades the user chose); record **all qualifying signals and no-trade outcomes** during observe/forward testing to estimate opportunity-level performance.
- No AI guarantee of profit, no silent strategy rewriting, no invented fills/counterfactuals.

## Intended workflow
**DEFINE → JOURNAL → TEST → VALIDATE → PLAN → APPROVE → EXECUTE LOCALLY → RECORD → REVIEW → LEARN**
1. Trader defines named, immutable-versioned strategies, indicators, confluences, session, market conditions, entry, invalidation, stop, targets, sizing, expiry, and maximum risk. Changes create new versions.
2. Trader may review charts at home, identify a *possible* strong setup, annotate/screenshot it, and create an immutable **pre-trade plan** in EdgeLog. The plan is distinct from the post-trade journal. A plan can remain waiting, expire, invalidate, be canceled, be rejected, or execute.
3. EdgeLog may recognize objective setups from historical/live OHLCV and other required market data with deterministic definitions; custom STD/JBlocks/FVG logic must be specified/tested. Screenshot AI is **advisory**, may mark UNKNOWN, and needs trader confirmation; it is not the execution authority.
4. Evaluate hypothesis from journal trades and, later, all observed opportunities: expectancy in R **after costs**, win/loss/BE, average win/loss, profit factor, max drawdown, MFE/MAE when valid, sample size, confidence/uncertainty, market/session regime, plan adherence, touch/intervention delta. Separate in-sample discovery from out-of-sample and forward testing. No threshold or win rate alone proves an edge.
5. Trader reviews entry, direction, contract, qty, stop, targets, risk and expiry; authorizes a **bounded plan locally** for TopstepX **Practice**. A cloud/web approval can save a pending intent, but may **not** trigger or relay an order. Local device must independently confirm/authorize execution.
6. Windows companion executes and manages provider orders **on the user's own computer**, subject to independent risk limits, provider-native protection where verified, stale-data/disconnect/restart reconciliation, kill controls, and duplicate-submission protection. Initial ST1 = manually approved **limit order only**; **not unattended stop/target management**. Do not permit walk-away claims before #55 is tested.
7. Local append-only audit records plan ID/version, signal and authorization, account/contract, submission, provider order IDs, acknowledgements, fills/partial fills, stops/targets, modifications, rejects, cancels, closes, fees when available, timestamps, reconciliation/errors and human touches. Idempotently sync objective events to existing canonical **TradingDay/Trade/TradeEntry/TradeExit**; do not create a parallel journal store. Preserve no-trade plans as their own records. Calculate realized P&L/R only when supported; label unknown otherwise.
8. Trader later opens EdgeLog and sees planned vs actual, realized result, what changed and why, setup match vs empirical validation vs discipline, and completes **their own** psychology/reflection. Automatic facts reduce clerical work; no auto-written psychological journal.
9. **Did you touch your trade?** Keep original plan immutable, capture modifications and reasons, calculate untouched counterfactual only if enough market-path data makes it determinable; otherwise mark unknown or user estimate (#48).
10. Missed journal day doctrine remains: **One missed day is data, not a pattern. Don't miss twice.** (#46)

## Technical split — one product, two runtime components
- **DigitalOcean App Platform WEB**: frontend, FastAPI API, auth, journal, strategy definitions, validation analytics, planned-trade records, read-only agent status, synchronized results. DEV and PROD isolated.
- **Local Windows companion / agent**: TopstepX/ProjectX credentials, market/account/order streams, authorization, risk checks, actual order origination/modification/cancellation, provider reconciliation, durable local audit. Cloud **must never originate, relay, modify, cancel or automatically trigger orders**. Cloud not a trading control plane.
- User may visually inspect external charts initially; integrated charts and automatic setup detection are future milestones, not existing functionality.

## Status / dependencies (as of owner discussion; verify PR and runtime state before execution)
- ST0 local agent foundation: PR #31 merged, **does not prove live Practice connection**.
- ST1 Practice manual limit order: #26 / PR #33 open, **not owner accepted**.
- Windows companion #53; plan→local approval #54; protective order lifecycle #55; recorder #56: **issues created, not implemented**.
- Strategy contract observe-only #27; risk engine/Practice auto #28; unified control panel/journaling #29; analytics #30; trader-defined confluence grading #32; touch counterfactual #48. Treat overlap as dependencies; avoid duplicate stores or independent apps.
- Strategy validation milestones: SV1 versioned definitions, SV2 structured journal/plan and objective event quality, SV3 transparent edge analytics, SV4 out-of-sample and observe-only/forward testing. **Do not label a self-declared setup A+ as proven.**
- Existing P3.5 visual workspace PRs (#43 and #49) overlap; owner gate and reconciliation still needed. No silent merge.
- Follow GitHub issue → implementation PR → exact DEV deploy → owner PASS/FAIL → merge → separate explicit PROD deploy.

## New highest priority: DigitalOcean App Platform web migration
**Owner explicitly prioritizes moving the WEB app to DigitalOcean App Platform now.** See **#57**. This is a change to prior 'P3.5 first' scheduling; preserve open visual work without merging it prematurely.
- Audit Vue/Vite static frontend, FastAPI service, /api same-origin routing, cookies, DB, Alembic, screenshots/persistent files, secrets, health and build/runtime.
- Separate DEV `d.edgelog.trade` and PROD `edgelog.trade` with separate databases/secrets. Plan persistent managed PostgreSQL/object storage as necessary; local droplet files/DB do not magically migrate.
- First establish a repeatable DEV App Platform deployment and test all core workflows, then plan production data migration, backups/restore, DNS cutover and rollback.
- Keep existing droplet production operational until **explicit owner-approved** cutover; do not assume any migration is complete.
- **Windows agent stays on user's computer**; do not deploy it to App Platform.

## Scope and safety
Practice first. Explicit owner acceptance and verified platform/API behavior required before unattended Practice management; any non-Practice/live order capability is a separate future authorization and test gate. No cloud-originated trading, no guaranteed returns, no inferred fills, no automatic rewriting of trader reflections.
