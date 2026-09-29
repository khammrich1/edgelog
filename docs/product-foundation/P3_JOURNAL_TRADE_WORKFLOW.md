# P3 — Daily Journal & Trade Workflow UX

See issue #undefined.

## North Star

**Prepare → Trade → Review**

P3 makes the Daily Journal a cohesive trading workstation using the P1 visual system and P2 workspace composition.

## Required outcomes

- Intentional desktop content width, gutters and hierarchy; eliminate the narrow/off-center form floating in dead space.
- Preserve the Mood & Bias / Trades / Overview journal flow.
- Improve Mood & Bias preparation hierarchy without changing its stored meaning.
- Make full trade entry + existing trade review feel like one workflow.
- Keep Setup required for new trades and preserve all established trade behavior.
- Make Overview useful for end-of-day review using truthful existing data.
- Maintain selected date/state across tabs and preserve Dashboard/Calendar deep links.
- Locked days remain clearly read-only.
- Preserve responsive behavior.

## Non-goals

No Trade Ranker implementation, AI grading, Strategy Trader execution, new analytics engine, pricing, marketing, or unrelated data-model redesign.

## Owner gate

Deploy the exact P3 PR to DEV. Kyle tests the three tabs, persistence, trade workflow, date navigation and locked-day behavior. PASS is required before merge.
