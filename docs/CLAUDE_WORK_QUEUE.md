## CURRENT COORDINATION — October 15, 2026 (Pacific)

**Immediate goal: dependable daily journal and broker-data verification, not feature expansion.** This section supersedes older CURRENT priority labels below for near-term sequencing, without changing the longer-term product vision.

| Issue / PR | Checked status / gate | Next action |
|---|---|---|
| #84 / PR #81 | Merged; manual completed-trade entry, commission/fee and net P&L groundwork | Verify DEV deployment and journal behavior; broker fees are not automatic |
| #82 | Open daily-use acceptance | Owner tests Today, checklist, Plan/Outcome, EOD persistence in DEV |
| #62 / PR #85 | Open draft, P&L regression tests; reported display discrepancy remains owner gate | Review, test representative MNQ trade, merge only after PASS |
| #83 / PR #86 | Open draft, interactive multi-account agent selection | Local Windows acceptance, Practice safety, then owner merge approval |
| #61 / PR #87 | Open draft, break-even exit action | Test partial-exit B/E and P&L in DEV; owner gate |
| #80 / PR #88 | Open draft, read-only TopstepX history diagnostic | Review and run locally against real selected account; collect redacted field-presence report; no DB writes |
| #70 / #57 | DEV migration/auth verification remains an open issue gate | Confirm current DEV auth, API, migrations and journal persistence; do not infer production readiness |

**Two broker flows, not interchangeable:** Flow A is live provider-event execution tracking under ST1/PR #33 (not merged, no authorization for live trading). Flow B is explicit end-of-day, account/date-scoped read-only history and canonical journal reconciliation under #80. They must share provider/account identity and avoid duplicate trades; imported objective facts may prefill, but reflection remains trader-authored. No agent-to-cloud import connection is currently verified. Do not invent fee breakdowns from unverified API response fields.

**Recommended order:** (1) owner DEV daily-use acceptance #82 and correctness checks #62; (2) local #86 account-selection acceptance; (3) run PR #88 diagnostic against real TopstepX account and inspect redacted report; (4) scope next #80 reconciliation slice based on verified API contract. Keep #87 as an independent acceptance gate. Follow issue → PR → exact DEV/local testing → owner PASS → merge → separate production approval. Never merge or deploy merely because tests pass.

# Claude Open-Issue Work Queue

## CURRENT OWNER DECISION — October 11, 2026 (Pacific)

**Product:** one integrated trading decision platform. Research and validate trader-defined edges → deterministic setup recognition → **alert trader → require explicit entry approval** → independently authorized local Windows TopstepX Practice execution → safeguarded rule-based management (future, not accepted) → canonical review. No autonomous entry and no cloud order relay. The primary execution view is plan/status-first rather than chart-first. **LockedIn / lockedin.trade is a brand candidate only**; continue using EdgeLog. Authoritative spec: [PRODUCT_DIRECTION_2026-10-11.md](PRODUCT_DIRECTION_2026-10-11.md), issue #59.

**P0 remains #57 DEV acceptance:** owner reports DigitalOcean login page and /health work, but API route, Supabase/Alembic, auth/session, journal CRUD and uploads are not yet verified. Do not claim full DEV PASS, migration completion, or production deployment. **Next work:** finish DEV smoke tests and migrations without touching PROD; then issue-linked observe-only signal/alert proposal contract from #59. All order placement and unattended management remain separately gated (#26, #53–#56).

**PR #52 (issue #51 visual polish) reconciliation — October 12, 2026:** owner authorized merging current `main` into PR #52's branch (`codex/visual-polish-pass`) to bring it forward from its `#49`-era base to current `main`, preserving this section's Oct 11 product direction and all other newer docs/routes/features/tests. See the "Visual follow-up" note below for #52's own scope; that note is now historical relative to this one.


## CURRENT OWNER PRIORITY — October 8, 2026 (Pacific)

**P0 — DigitalOcean App Platform web migration #57 is now first.** Prepare audit and repeatable isolated DEV app; owner DEV PASS before a separately authorized production DB/DNS cutover. No claim of deployment. **Do not deploy local Windows TopstepX agent to App Platform; cloud must not originate or relay orders.** Preserve existing P3.5 candidate PRs #43/#49 without silent merge; resume their acceptance after the infrastructure priority or as explicitly authorized. Full updated one-product strategy-validation and Practice execution spec: [PRODUCT_VISION_AND_EXECUTION_2026-10-08.md](PRODUCT_VISION_AND_EXECUTION_2026-10-08.md). New backlog #53–#56 builds on #26/PR #33; no new execution code accepted. The historical 'CURRENT P3.5' and 'Strategy Trader parked' headings below are superseded for sequencing by this update.

## Visual follow-up - October 8, 2026 (Pacific)

PR #49 is merged; PR #43 was closed as superseded and #50 is closed.
Issue #51 scopes the owner's new visual improvement pass. It preserves the
accepted workspace layout and requires fresh DEV owner acceptance before merge.
Production deployment remains a separate owner decision. Older candidate
status statements below are historical. Strategy Trader remains parked.

## Owner revision - October 7, 2026 (Pacific)

Owner subsequently selected PR #49 as the preferred workspace candidate.
Continue the #50 correction on #49 and test that PR first. Keep #43 unmerged;
reconcile/close it as superseded after #49 receives explicit DEV PASS. Visual
preference does not claim functional acceptance, merge, or production deploy.

Owner requested a broader workspace correction after DEV testing PR #49.
Issue #50 records that revision under P3.5/#41. PR #49 is the current correction
candidate; PR #43 remains open and overlapping. No new owner PASS or merge is
claimed. Choose/accept one candidate before reconciling overlapping PRs.
P4 onboarding and #32 follow P3.5; #45/#46/#48 remain scoped backlog.
Strategy Trader remains parked. See `docs/PRODUCT_REVIEW_2026-10-07.md`.

## Current coordination — October 4, 2026 (Pacific)

P1 #36 and P2 #38 are accepted/merged. P3 #40 is merged with the recorded functional pass. P3.5A #42 is merged; **P3.5B #43 is open for DEV owner acceptance**, covering Dashboard, Daily Journal and Calendar. P3.5C remains follow-up under #41. Check the exact DEV revision before testing; no fresh production deployment is claimed.

**Tilt Journal #45** is scoped, not delivered: CBT-informed Trigger → Thought → Emotion → Urge → Behavior → Consequence → Reframe → Recovery → later reflection. Catching/interruption (“I caught it”) is success. **Missed Day Recovery #46** is scoped: **One missed day is data, not a pattern. The only rule: don't miss twice.** An expected journal day excludes weekends/non-trading days, market holidays and planned time off. One miss invites a return; it does not erase progress or prove a broken process.

Keep the customer-facing foundation first. Strategy Trader ST1 #33 is still open/parked. Order origination and credentials remain on the owner's personal Windows device. No execution work is resumed by this update.

The current GitHub issues/PRs and [portfolio board](https://github.com/khammrich1/ProjectStatus/blob/main/boards/EDGELOG.md) supersede stale queue/current-status labels in the older history below. No feature implementation, release or new owner acceptance is claimed.



This file establishes the current owner-authorized coordination queue for EdgeLog. Individual GitHub issues remain the source of truth for scope and acceptance criteria.

Convention: an **issue** is the authoritative backlog/specification record. Claude normally creates the **implementation PR** from the issue. The PR is the actual review/deploy/test unit.

## Current priority — customer-facing product foundation

Strategy Trader is temporarily parked while the core EdgeLog product becomes customer-presentable.

- P1 — Product shell & visual system: accepted / merged (#36).
- P2 — Dashboard / first impression: accepted / merged (#38).
- P3 — Daily Journal & trade workflow UX: issue #39 / PR #40, merged with recorded functional pass. Functional owner testing passed; latest layout is materially improved and the remaining broad visual-depth concern has been moved out of P3.
- **CURRENT: P3.5 — #41.** A / #42 is merged; B / #43 is open for DEV acceptance; C follows the applicable owner gate. This is a shared-system pass across Dashboard, Journal, Calendar, Trades, Stats, and future Trade Ranker surfaces — not a Daily Journal-only restyle.
- P4 — Onboarding follows P3.5.
- Define Your Edge / Trade Ranker follows the customer-facing foundation sequence as scoped/authorized.

### P3.5 visual target

The current UI is too flat: too many graphite rectangles live on the same plane and hierarchy depends too much on labels/borders.

Target:

- onyx base canvas with intentional layered graphite surface levels;
- stronger depth and hierarchy without decorative clutter;
- fewer generic boxed cards / less card soup;
- deliberate dividers, grouping, and negative space;
- dense professional trading-workstation / premium-journal character;
- condensed uppercase hierarchy where appropriate;
- restrained copper used to direct attention;
- one shared component language applied consistently across major screens;
- preserve the information architecture and workflows already validated in P1–P3.

## Product doctrine — do not optimize journaling away

**You traded it. You journal it. You own it.**

EdgeLog is manual-first. The act of reviewing and journaling a trade is intentional product value, not friction to eliminate.

- AI/screenshot capture may prefill candidate facts, but the trader confirms them.
- Future execution integration may prefill objective execution facts, but must not silently complete a journal entry.
- Setup/context/psychology/reflection and deliberate journal completion remain the trader's responsibility.
- Analytics are downstream of journaling.

Core product loop: **Plan → Trade → Journal → Reflect → Improve**.

## Strategy Trader — PARKED, NOT ABANDONED

- ST0 / PR #31: merged.
- ST1 / PR #33: parked/open; do not merge merely to clear the queue.
- #27–#29 remain later Strategy Trader dependencies.
- #30 Strategy Analytics remains deferred until canonical strategy execution metadata exists.

Strategy Trader order origination must stay on the trader's personal device. TopstepX credentials remain local. EdgeLog cloud is never the order relay.

When this work resumes, it must preserve the manual-journaling doctrine: execution knowledge may prefill facts but does not silently complete reflection/journaling.

## Other backlog

- #4 — Future slice: Mentorship groups and daily check-in dashboard
- #5 — Future slice: Required pre-trade daily check-in for mentorship members
- #6 — Future slice: Mentor mentee detail view with check-ins and trades
- #32 — Trade Ranker: personal A+ setup grading; trader-defined setups/confluences/versioning with advisory AI assistance and user confirmation.

## Delivery rules

- Read and reference the authoritative issue before implementation.
- Normal handoff: **Issue/spec → Claude implementation PR → assistant review → exact PR DEV deploy → owner PASS/FAIL → same-PR fixes or merge → explicit production deploy.**
- Keep implementation traceable to its issue.
- Use canonical EdgeLog Trading Day / Trade / TradeEntry / TradeExit data rather than parallel stores.
- No production deployment or major milestone merge without owner acceptance.
- Keep accepted documentation synchronized with implemented behavior.
