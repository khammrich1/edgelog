# EdgeLog Product Specification

## Identity

**EdgeLog** is a standalone trading journal.

- Domain: `edgelog.trade`
- Owner: Green Bread Enterprises LLC
- Operating line: Green Bread Trades
- Brand phrase: **Find Your Edge.**
- Product loop: **Plan → Trade → Journal → Reflect → Improve**

## Product positioning

EdgeLog is a trading journal centered on **intentional manual journaling**. Traders record preparation, market bias, trades, execution, psychology, mistakes, discipline, reflections, and results so they can determine both whether their defined edge is supported by their data and whether they are actually following it.

EdgeLog is intentionally distinct from an automated-import-first journal. Removing the act of journaling is not the goal.

### Product doctrine

**You traded it. You journal it. You own it.**

The deliberate work of reviewing a trade is part of the product. A trader should revisit what they planned, what setup they took, what they actually executed, what happened, what they felt/did, and what should change.

EdgeLog should reduce clerical friction without removing reflective friction:

- manual journaling remains the primary workflow;
- screenshot/AI capture may prefill candidate facts, but the trader reviews and confirms them;
- future Strategy Trader/execution integration may prefill objective execution facts, but must not silently complete the journal;
- imported or known execution data does not substitute for setup classification, context, screenshots where useful, psychology, reflection, or deliberate completion;
- analytics are downstream of journaling and exist to reveal patterns in the trader's own process and data.

A useful internal standard for the product is: **if a trader will not take the time to journal and review their trades, EdgeLog should not optimize the discipline out of the process.**

EdgeLog is not primarily a broker, signal service, trading bot, automated trade importer, AI trading platform, or social network.

## Questions EdgeLog should answer over time

- What setups actually work for this trader?
- Where do losses come from?
- What conditions produce the best trading?
- How does psychology affect performance?
- Is the trader following their own process?
- Where does the trader's actual statistical edge exist?

## MVP stop line

MVP must let a trader:

1. define their own setup/edge;
2. prepare for the trading day;
3. deliberately journal trades and execution;
4. record psychology/context and reflect;
5. review daily/weekly performance;
6. see core analytics that distinguish edge quality from execution/process adherence.

MVP does not require feature parity with other journals, every broker integration, a huge analytics library, or an automated edge finder. Once the core path is owner-accepted and customer-presentable, freeze feature expansion and put the product in front of paying traders.

## Visual identity

EdgeLog should feel like a **professional field instrument + premium trading journal**, not a generic SaaS dashboard.

Foundation:

- Onyx base canvas
- Layered graphite surfaces with intentional depth
- Steel dividers, borders, and muted text
- Off-white primary text
- Restrained copper for identity, selection, action, and emphasis
- Green/red reserved for functional profit/loss and Long/Short meaning where established

### P3.5 visual direction

The current product is functionally stronger but still visually too flat. P3.5 must rebuild the **shared cross-product visual system**, not restyle only the Daily Journal.

Apply a consistent component/workspace language across:

- Dashboard
- Daily Journal
- Calendar
- Trades
- Stats
- future Trade Ranker surfaces

Design targets:

- intentional surface levels and depth without decorative clutter;
- fewer generic boxed cards / less card soup;
- stronger hierarchy through typography, dividers, grouping, and negative space;
- dense, readable trading-workstation composition;
- condensed uppercase hierarchy where appropriate;
- restrained copper rather than copper everywhere;
- selected/expanded content should retain context rather than forcing unnecessary navigation;
- responsive/mobile behavior remains first-class.

Avoid neon UI, excessive glow/gradients, crypto aesthetics, bulls/bears, money graphics, Wall Street clichés, giant decorative cards, and unnecessary animation.

## Trade Ranker direction

EdgeLog does not define a universal A+ trade. **The trader defines their own edge.**

Core direction:

**Define setup → rank trade → log outcome → discover edge**

Setups should become named/versioned definitions with trader-defined confluences and grading thresholds. Screenshot/AI assistance is advisory: the trader confirms/rejects/corrects the assessment. Historical trades preserve the setup/version used at trade time.

## Strategy Trader direction

Strategy Trader is **parked, not abandoned** while the customer-facing foundation is completed.

Execution North Star:

**Plan → Validate → Take Trade → Track → Journal/Learn**

Order origination must remain on the trader's personal device. TopstepX credentials remain local. EdgeLog cloud may handle planning, configuration/status, journaling, analytics, and execution results, but is not an order relay.

Even when execution integration knows a trade occurred, it may prefill objective facts only. The trader still deliberately completes the journal/review.

## Development model

EdgeLog uses owner-test-gated vertical slices.

Standard flow:

1. Owner + assistant scope the work.
2. Create an authoritative GitHub Issue/spec.
3. Claude creates/uses the implementation PR.
4. Assistant reviews the PR.
5. Deploy the exact PR candidate to `d.edgelog.trade`.
6. Owner manually tests and gives PASS/FAIL.
7. FAIL stays on the same PR for correction/retest.
8. PASS merges to `main`.
9. Production deployment is a separate explicit step.

Do not implement future slices early or create speculative infrastructure without a current need.

## Current product-foundation sequence

- P1 — Product shell & visual system: accepted / merged.
- P2 — Dashboard / first impression: accepted / merged.
- P3 — Daily Journal & trade workflow UX: current owner gate in PR #40; functional acceptance passed and the latest layout is materially improved.
- **P3.5 — Cross-product visual system / workspace rebuild: next.**
- P4 — Onboarding.
- Define Your Edge / Trade Ranker.
- Pricing/subscription presentation.
- Public marketing/landing experience.
- Resume deeper Strategy Trader work when the core product is customer-presentable.

The repository roadmap contains older numbered vertical-slice history as well as future feature direction. This product-foundation sequence is the current near-term priority.
