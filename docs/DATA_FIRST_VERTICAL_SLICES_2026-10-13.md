# EdgeLog — Data-First Vertical Slice Plan
**Owner direction: October 13, 2026.** This is the active proposed implementation sequence for collecting evidence. Preserve the canonical [ROADMAP.md](../ROADMAP.md), [EDGELOG.md](../EDGELOG.md), and [product vision](PRODUCT_VISION_AND_EXECUTION_2026-10-08.md). Do not interpret this plan as delivered functionality or approval to trade automatically.

## North star
**DEFINE → JOURNAL → TEST → VALIDATE → PLAN → APPROVE → EXECUTE LOCALLY → RECORD → REVIEW → LEARN.**
The trader defines a hypothesis; EdgeLog collects trustworthy evidence to test it. Setup/checklist match, empirical strategy validation, and execution discipline are distinct. Do not declare A+ statistically proven from confluence count. Manual reflection is essential. Reduce clerical friction, not reflective friction.

## Data rules across all slices
1. Existing TradingDay/Trade/TradeEntry/TradeExit are canonical; do not build parallel trade storage.
2. Capture pre-trade intent separately from post-trade outcomes. Preserve strategy version and time of observation. Changes are auditable, not silently rewritten.
3. Record source/provenance (manual, screenshot-assisted, later provider-observed), observed vs inferred, timestamps, and explicit unknowns. Never fabricate fills, market context, emotions, or R.
4. Structured fields support analysis; optional narrative preserves human context. Keep capture practical enough for daily use.
5. Keep cash/prop-firm financial ledger separate from trade P&L.
6. DEV first; owner tests each slice; no PROD changes without separate authorization. No cloud-originated broker orders.
7. Preserve existing historical data, nullable legacy fields and backwards-compatible reads where possible. Versioned migrations and rollback plan for schema changes.
8. Do not block data capture on analytics/UI polish. Build only the minimum needed to collect correct observations.

## Current baseline (verify at implementation time)
- VS1–VS3 journal/trade foundation, calendar, Today Overview, and financial ledger exist; the Overview is **not** the future evidence analytics.
- PR #65 merged: screenshot confirmation/provenance, DEV migration 009 applied; real broker screenshot acceptance still needed.
- PR #76 merged: Mood/Sleep rapid-click issue persists in owner video; **deferred**, not accepted as fixed. Do not touch unless separately reprioritized.
- DEV App Platform + isolated Supabase PostgreSQL functioning; PROD remains separate legacy deployment.
- #32 setup/ranker, #30 strategy analytics, #48 intervention counterfactual, #33 local Practice agent remain separate existing work; avoid duplicate tickets.

## Data-first vertical slices and gates

### DF-VS0 — Capture contract and gap audit (START HERE)
**Goal:** know exactly which fields, endpoints, migrations and UI controls already collect the evidence required for future validation.
**Work:** map existing schema/API/UI to pre-trade intent, trade facts, execution, context, psychology, debrief, provenance, strategy identity and versions; distinguish present, optional, absent, derived and unreliable. Audit edits and overwrites. Produce a field-level data dictionary and prioritized minimal gaps; no implementation yet.
**Gate:** owner approves the minimal DF-VS1 capture contract; no duplicate schema or speculative analytics. **Read-only** audit, no deployment.

### DF-VS1 — Daily evidence and trade debrief capture
**Goal:** reliably collect daily observations immediately.
**Scope:** fill approved gaps only: planned-vs-actual execution, rule adherence (yes/no/unknown + reason), interventions and rationale, short post-trade and end-of-day reflection, as needed after DF-VS0. Make pre-trade versus post-trade timestamps explicit. Existing mood, sleep, bias, trades and screenshots remain canonical.
**Gate:** owner logs a representative trading day with multiple trades, a partial exit, a rule violation and a no-trade day; save/reload preserves exact entries, including unknowns; no forced invented data.

### DF-VS2 — Define Your Edge, versioned setup contract (existing #32 / LI-VS1)
**Goal:** make each trade attributable to the actual strategy hypothesis in force.
**Scope:** trader-owned setup definitions, versioned confluences, entry/invalidation/stop/risk and optional market/session conditions; immutable version references from trades/plans; migration for legacy free-text setup values without retroactively asserting a version.
**Gate:** changing a setup creates a new version; historical trades retain their original definitions. Match grade is labeled separately from proven edge.

### DF-VS3 — Capture consistency and 30-day pilot
**Goal:** collect a usable sample of real observations, not 30 fabricated or forced sessions.
**Scope:** light-weight completion visibility, missed-day recovery respecting weekends/holidays/planned off-days (#46), clear missing-data indicators, export/backup verification, usability fixes only. Begin real journaling before this slice when possible.
**Gate:** 30 **actual expected trading days** reviewed for completeness, timestamp/source accuracy and capture burden. This is a collection milestone, **not** a statistical proof threshold.

### DF-VS4 — Baseline analytics (LI-VS2, existing #30)
**Goal:** transparent descriptive analysis of captured data.
**Scope:** net realized P&L and R only when derivable, costs where known, sample size, win/loss/BE, setup/version splits, adherence, session/context splits and explicit missing-data warnings. No performance claim on insufficient evidence; no cherry-picked A+ badge.
**Gate:** reconcile sample calculations against source trades and explain excluded records, uncertainty and denominators.

### DF-VS5 — Plan, intervention and counterfactual evidence (existing #48 / #54)
**Goal:** preserve immutable planned risk/entry/exit intent and subsequent human touches.
**Scope:** planned trade lifecycle including canceled/expired/no-trade, intervention event/reason history, planned vs actual. Counterfactual only when enough market-path data exists; otherwise unknown/user estimate.
**Gate:** plan cannot be rewritten by later outcomes; replay of changes and provenance is inspectable.

### DF-VS6 — Observe-only opportunities and forward validation (LI-VS3, #27/#59)
**Goal:** reduce selection bias from journaling only executed trades.
**Scope:** deterministic versioned candidate detection, data freshness, qualifying signal and rejected/no-trade history, regime and forward-observation cohorts. No order submission.
**Gate:** signal replay and no-trade evidence; distinguish in-sample discovery from out-of-sample/forward observation.

### DF-VS7 — Evidence-based strategy health and opportunity proposal (LI-VS4/7)
**Goal:** help traders identify supported opportunities without constant chart-watching.
**Scope:** uncertainty-aware strategy health, candidate evidence, sample size, plan proposals with explicit approve/reject/edit and expiry. Candidate does not authorize execution.
**Gate:** honest evidence and risk labels; no unsupported certainty or guaranteed edge.

### DF-VS8 — Local Practice execution and objective recording (LI-VS5/6, #33/#53–#56)
**Goal:** reconcile actual provider events into the existing journal.
**Scope:** owner-approved, bounded TopstepX Practice orders from local Windows companion; local credentials and kill controls; idempotent provider events, fills, partial exits, rejects and fees; plan-based management only after separate safety acceptance.
**Gate:** owner Practice tests, duplicate/restart/disconnect/protection verification. Cloud never originates or relays orders. Live trading is a separate future approval.

## Sequencing and handoff
- **Now:** DF-VS0 read-only capture audit. Its findings determine the exact DF-VS1 fields; do not pre-commit to speculative migrations.
- **Then:** DF-VS1 capture workflow, DF-VS2 versioned setups, start/continue 30-day pilot, DF-VS4 analytics.
- **Later:** DF-VS5–8 in dependency order with separate gates.
- Standard handoff: issue/spec → Claude investigation/PR → exact DEV deploy → owner PASS/FAIL → merge, adapting DEV branch/deploy logistics explicitly; PROD always separate.
- Each PR must report changed data fields, migration impact, provenance/legacy behavior, tests and owner test steps.
