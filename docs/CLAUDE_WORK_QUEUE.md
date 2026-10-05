# Claude Open-Issue Work Queue

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
