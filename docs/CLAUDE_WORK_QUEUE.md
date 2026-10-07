# Claude Open-Issue Work Queue

## Current coordination — October 7, 2026 (Pacific)

Issues #37 (P1) and #39 (P3) are closed -- both delivered and merged (PR #38, PR #40) with recorded functional passes; closing them just catches up GitHub bookkeeping to what `status.md` already recorded as accepted. P3.5A #42 is merged. **P3.5B #43 is still open**, unmerged: the owner's DEV visual pass (Dashboard/Calendar/Mood & Bias) and a Claude-run scripted functional check (Trades + Overview controls/data/navigation, no issues found) are both done -- it is waiting only on the owner's final pass and merge. **P3.5C (Trades/Stats/Settings consistency) has not been started** -- per the explicitly agreed structure, it does not begin until #43 merges.

Three new issues are scoped but explicitly **not authorized to interrupt P3.5**, each carrying "do not interrupt currently authorized P3.5 work unless Kyle explicitly reprioritizes" in its own body: **Tilt Journal #45** (CBT-informed Trigger → Thought → Emotion → Urge → Behavior → Consequence → Reframe → Recovery → later reflection; catching/interrupting the urge is success). **Missed Day Recovery #46** (one missed day is data, not a pattern; the only rule is don't miss twice; an expected journal day excludes weekends/non-trading days, market holidays and planned time off; one miss invites a return, it does not erase progress). **Trade Management Counterfactual #48** (opened 2026-10-07): captures whether the trader "touched" a closed trade after entry (moved stop/target, exited early, re-entered, etc.) versus executed the plan as documented, records the counterfactual untouched-plan outcome only when determinable (never fabricated), and measures an intervention delta -- separating edge quality from management interference. None of #45/#46/#48 has implementation started.

Keep the customer-facing foundation first. Strategy Trader ST1 #33 is still open/parked. Order origination and credentials remain on the owner's personal Windows device. No execution work is resumed by this update.

The current GitHub issues/PRs and [portfolio board](https://github.com/khammrich1/ProjectStatus/blob/main/boards/EDGELOG.md) supersede stale queue/current-status labels in the older history below. No feature implementation, release or new owner acceptance is claimed.



This file establishes the current owner-authorized coordination queue for EdgeLog. Individual GitHub issues remain the source of truth for scope and acceptance criteria.

Convention: an **issue** is the authoritative backlog/specification record. Claude normally creates the **implementation PR** from the issue. The PR is the actual review/deploy/test unit.

## Current priority — customer-facing product foundation

Strategy Trader is temporarily parked while the core EdgeLog product becomes customer-presentable.

- P1 — Product shell & visual system: accepted / merged (#36, closed). PR #38.
- P2 — Dashboard / first impression: accepted / merged. Issue #37 (closed) / PR #38.
- P3 — Daily Journal & trade workflow UX: issue #39 (closed) / PR #40, merged with recorded functional pass. Functional owner testing passed; latest layout is materially improved and the remaining broad visual-depth concern has been moved out of P3.
- **CURRENT: P3.5 — #41 (open, parent issue).** A / #42 is merged. **B / #43 is open, unmerged** -- owner DEV visual pass done, Claude's scripted functional check of Trades + Overview done (no issues found); waiting on the owner's final pass and merge. **C has not started** and does not begin until #43 merges. This is a shared-system pass across Dashboard, Journal, Calendar, Trades, Stats, and future Trade Ranker surfaces — not a Daily Journal-only restyle.
- P4 — Onboarding follows P3.5.
- Define Your Edge / Trade Ranker follows the customer-facing foundation sequence as scoped/authorized.

### Scoped, not authorized to interrupt P3.5

Each of these issues explicitly states it must not interrupt the currently authorized P3.5 work unless Kyle reprioritizes. None has implementation started.

- **#45 — Tilt Journal.** CBT-informed reflection chain (Trigger → Automatic Thought → Emotion → Urge → Behavior → Consequence → Challenge/Reframe → Recovery Action → Later Reflection). Key product nuance: successfully feeling an urge and *not* acting on it ("I caught it") must be recorded as a process win, not a failure.
- **#46 — Missed Day Recovery.** "One missed day is data, not a pattern. The only rule: don't miss twice." Requires distinguishing a genuinely missed *expected* journal day from a legitimate no-journal day (weekends, holidays, planned time off) before anything is treated as a miss; recovery UX must be lightweight and non-punitive, and must not auto-create a Tilt Journal entry.
- **#48 — Trade Management Counterfactual** (opened 2026-10-07). Asks "Did you touch this trade?" post-close, and if so, "What would have happened if you didn't touch it?" Must preserve an immutable original-plan snapshot at entry time, never fabricate an untouched-outcome counterfactual when price-path data is insufficient (label it indeterminate/estimated instead), and never auto-label a touched trade as tilt/a mistake. Suggested slices: TMC1 (capture) → TMC2 (counterfactual calculation) → TMC3 (analytics).

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
