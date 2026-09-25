# EdgeLog Vertical Slice Roadmap

EdgeLog is built and accepted one vertical slice at a time. Future slices establish direction only; they are not authorization to implement them early.

## VS1 — Foundation

**Accepted.**

Goal: create the standalone EdgeLog application foundation.

Includes:

- project initialization
- EdgeLog branding and SVG mark
- copper / graphite / steel / onyx design system
- responsive application shell
- registration, login, logout
- persistent secure authentication
- minimal user/account model
- PostgreSQL foundation and migrations
- production configuration
- automated and manual VS1 testing

Acceptance: a user can register, log in, refresh without losing the session, access the protected shell, log out, and use the app on desktop/mobile.

## VS2 — Daily Journal Core

**Accepted.**

Goal: establish the trading day as the center of EdgeLog.

Planned:

- journal calendar / day selection
- trading-day record
- sleep quality
- mood
- configurable morning checklist
- market bias / thesis
- optional bias chart screenshot
- trading-day lifecycle/status
- lock/unlock where appropriate

The Daily Journal calendar represents the trader's **day and process**, not individual trade cards.

## VS3 — Trade Lifecycle

**Accepted and merged**, including the pulled-forward work below. Two gaps remain against the original list: no `Draft` trade state (trades go straight to `Open`), and no `reasoning`/`emotional state` per-trade fields (explicitly deferred by the user, not an oversight). R-multiple, listed below, ended up implemented as part of VS4 instead (client-side, since it's derivable from fields the API already returns).

Goal: accurately record a futures trade from idea through exit.

Planned:

- Draft / Active / Closed / Canceled states
- flexible symbols rather than a permanently hard-coded list
- Long / Short
- contracts
- entries
- stop
- targets
- trims / partial exits
- multiple exits
- setup type
- reasoning
- emotional state
- entry/exit notes
- automatic realized P&L
- R-multiple where sufficient information exists

Trade data created here becomes the source used by Trade Calendar and analytics. Do not duplicate trade records across features.

Built in this slice, ahead of its original roadmap position:

- **AI screenshot trade capture**, pulled forward from VS9 -- a dropzone on
  the trade entry form sends an uploaded broker screenshot to Claude, which
  extracts candidate symbol/direction/entry/stop/target/quantity fields to
  prefill the manual form. It never creates or saves a trade on its own; the
  trader still reviews and submits. See VS9 below for what that slice still
  owns.
- **Configurable trade setups** -- a Settings page lets the trader maintain
  their own list of setup/strategy labels, offered as a dropdown on the
  trade form (with free-text fallback), the same shortcut-not-restriction
  relationship the symbol dropdown has to `Trade.symbol`.

## VS4 — Trade Calendar

**Current authorized slice.** Built (PR #19); pending the user's manual acceptance pass on a deployed environment.

Goal: create a dedicated chronological visual view of actual trades.

This page is **separate from the Daily Journal calendar**.

### Primary desktop view

Default to a weekly trade calendar:

- Monday through Sunday columns
- previous/next week controls
- current week/date-range heading
- jump-to-date/calendar control
- multiple trade cards under the day they occurred
- visually quiet empty days

### Collapsed trade card

Show enough to identify the trade quickly, including where available:

- symbol
- date/time
- Long / Short
- setup
- status
- P&L and/or R-multiple

Use functional colors carefully:

- green for profit
- red for loss
- neutral for breakeven/open/canceled
- copper for selection/interactions

Do not turn whole cards into bright green/red surfaces. The UI stays predominantly onyx, graphite, and steel.

### Expanded trade card

Selecting a trade should reveal detail while preserving calendar context whenever practical.

May include:

- symbol and direction
- setup
- entry
- stop
- target
- exits/trims
- contracts
- realized P&L
- R-multiple
- trade grade
- reasoning
- notes
- emotional state
- chart/screenshot when available

### Visual direction

This slice should strongly follow the approved EdgeLog weekly-calendar reference:

- near-black / onyx background
- narrow icon-oriented navigation rail
- condensed/technical typography where appropriate
- thin steel grid lines
- graphite cards
- restrained copper border/highlight on selected content
- dense but readable information hierarchy
- professional logbook/instrument feel

The reference is inspiration, not a literal copy.

### Responsive behavior

Do not squeeze seven unreadable columns onto mobile.

Evaluate a mobile-specific presentation such as:

- horizontally scrollable days, or
- day-focused view with week selection

Choose based on usability during implementation/testing.

### Relationship to Daily Journal

Daily Journal answers: **How was my trading day and process?**

Trade Calendar answers: **What did I trade?**

A Trade Calendar day should eventually link to that day's Daily Journal, and the Daily Journal should show/link to its trades.

Do not implement before VS3 provides real trade data.

## VS4.5 — Annual P&L / Financial Tracker

**Accepted and built** (PR #20, extended by PR #21, #22, #23). Not part of the original numbered roadmap -- added mid-stream at the user's explicit request, sequenced to come after VS4. The user has since tested this live against the real Anthropic API (a real TopStep payout table) and reported two follow-up bugs, both fixed same-day: PR #22 (firm name vs. account ID) and PR #23 (duplicate-import detection + zero-amount entries for free resets).

Goal: track the actual cash economics of the trader's prop-firm business, separate from trade performance.

This ledger is **deliberately independent of Trade/TradingDay data** -- a payout is a profit-split fraction of trading results, not the same number as realized trade P&L, and the two must never be summed or reconciled against each other.

Includes:

- flat cash ledger: expense or income entries, each with category (free text), amount, date, optional firm/account (free text), optional notes
- both manual entry and AI screenshot capture (mirrors the trade-screenshot pattern: extraction only prefills the form, never auto-saves)
- per-entry screenshot upload/view/remove
- annual view with month-by-month income vs. expense bar chart, income/expense/net P&L summary tiles
- year navigation (prev/next/jump/this year)

Explicitly out of scope for v1 (per the requester's "get me something to work with and I will go from there"): configurable expense categories, multi-account/multi-currency support, recurring entries, budgets/tax handling, CSV import/export. The earlier idea of flagging/tracking strategies in Settings was raised in the same conversation but is a separate, not-yet-scoped idea -- not part of this slice.

**PR #21 addition -- bulk screenshot import**: the user's real payout screenshots (e.g. a TopStep payout-history page) show several finalized payouts in one table, not a single entry. Added a separate, opt-in "Import multiple from a screenshot" panel (collapsed by default, does not change the single-entry dropzone above): the AI extraction endpoint returns a list of candidate rows instead of one, shown as an editable, per-row-includable review table before anything is saved -- same never-auto-save rule as single-entry capture. Deliberately does not attach the source screenshot to the created entries (attaching one whole-table image identically to N entries added complexity for unclear benefit); a user who wants a screenshot on a specific bulk-imported entry can still add one afterward from the entries table's existing per-row control.

## VS4.6 — Admin Page (Account Roster, Traffic, Feedback)

**Accepted and built** (PR #24). Not part of the original numbered roadmap -- requested directly ("I need an admin page... similar to fitretro"), pulling forward a slice of VS17's "admin/user management" and "system/usage statistics" items rather than waiting for that slice's turn.

Goal: give the app owner visibility into who's using EdgeLog and what they think of it.

Includes:

- account roster: every registered user, when they signed up, whether they're an admin, and their most recent activity (date + page)
- 7-day traffic table: hits, unique authenticated users, and the auth/unauthenticated split, per page path
- a flat feedback list, fed by a new user-facing feedback form (nav-visible to everyone, not just admins)

Explicitly out of scope for v1: no display-name field on registration (roster shows email only), no in-app admin-management UI (the first admin is granted via one manual SQL update after the migration ships), no custom traffic date-range picker (fixed at 7 days), no feedback reply/status workflow, no page-view retention/pruning job. Traffic and "last activity" data only exists from the moment this shipped forward -- there's no way to backfill history from before the tracking beacon existed.

## VS5 — Daily Debrief

Goal: complete the daily loop: **Prepare → Trade → Review**.

Planned:

- bias result: correct / partial / wrong
- bias review notes
- automatic day P&L
- end-of-day notes
- emotional audit
- hardest moment / urge
- action actually taken
- expectation for tomorrow
- complete/lock day

## VS6 — Open Journal + Voice

Goal: capture observations that do not fit structured trade fields.

Planned:

- freeform daily journal
- timestamped entries
- editing/deleting
- attachments where appropriate
- quick entry
- voice dictation
- transcript cleanup while preserving meaning

Manual entry remains primary; voice is an easier input method, not the product identity.

## VS7 — Analytics V1

Goal: turn accumulated journal/trade data into useful feedback.

Planned metrics include:

- total and cumulative P&L
- win rate
- average winner / loser
- profit factor
- average R
- trade count
- best/worst days
- symbol performance
- setup performance
- Long vs Short
- date/symbol/setup filters
- selected process correlations where sample size supports them

## VS8 — Trade Calculator / Risk Planning

Goal: plan a trade before execution.

Planned:

- entry
- stop
- target
- account/risk inputs
- position size
- R:R
- futures point/tick value support
- planned vs actual result
- convert plan into a draft trade

## VS9 — AI Trade Capture

Goal: speed manual logging without making AI authoritative.

Planned:

- paste/drag/drop chart screenshot (pulled forward into VS3 at the user's explicit request -- see `POST /api/v1/trades/parse-screenshot`)
- infer candidate symbol/direction/prices/setup (implemented for symbol/direction/entry/stop/target/quantity; setup inference still pending)
- voice-to-draft trade entry
- user confirmation before saving extracted values (implemented: extraction only prefills the manual trade form, it never creates a trade on its own)

AI must never silently commit interpreted trade data.

## VS10 — Weekly Review

Goal: review the whole week as a coherent trading period.

Planned:

- weekly P&L and metrics
- bias accuracy
- setup patterns
- emotional/discipline patterns
- week rating
- what worked
- what hurt performance
- one change for next week

## VS11 — Psychology / Tilt

Goal: make trading psychology a first-class performance-journaling feature.

Planned:

- trigger
- thoughts
- emotion and intensity
- urge/action wanted
- action actually taken
- cognitive distortion tracking
- result
- recovery action
- optional links to a trade/day
- historical pattern review

Structured cognitive-behavioral techniques may inform these workflows, but EdgeLog should describe them as trading self-reflection/performance tools, not therapy, diagnosis, or mental-health treatment.

## VS12 — Discipline & Progression

Goal: reward process rather than trading frequency or raw profit.

Planned:

- XP transactions
- levels
- preparation/review/discipline XP
- useful streaks

Avoid rewards simply for placing more trades. A trader should be able to progress by correctly choosing not to trade.

## VS13 — Edge Discovery

Goal: identify statistically useful patterns in the trader's own history.

Potential analysis:

- setup expectancy
- symbol expectancy
- time-of-day performance
- day-of-week performance
- Long/Short expectancy
- R distribution
- performance after wins/losses
- mood/sleep/process correlations
- tilt correlation
- bias correlation
- planned vs unplanned trades
- rule adherence

Sample size and uncertainty must be communicated rather than presenting weak patterns as facts.

## VS14 — AI Coach

Goal: allow AI to analyze the trader's own EdgeLog history instead of providing generic trading advice.

Planned:

- daily/weekly debrief assistance
- pattern summaries
- trade critique
- discipline observations
- similar historical trade retrieval
- natural-language questions over journal history

Responses should be grounded in stored EdgeLog evidence.

## VS15 — Sharing / Profiles

Goal: selectively share parts of the trading journey without exposing private journal/psychology content by default.

Planned:

- profile
- public/private controls
- show/hide stats and trades
- individual trade/day sharing
- following/discovery only if it remains valuable to the product

## VS16 — Education

Goal: connect educational resources to the journaling product rather than create an unrelated content library.

Potential content:

- guides
- articles
- trading psychology
- risk management
- PDFs
- courses/lessons
- contextual recommendations based on journal patterns

## VS17 — Administration & Production Maturity

Goal: mature EdgeLog into an operable commercial product.

Planned as needed:

- ~~admin/user management~~ / ~~system/usage statistics~~ -- a first slice (account roster, 7-day traffic, feedback) shipped early as VS4.6; still open here: in-app admin-management (promoting/demoting admins), broader usage stats beyond page-view traffic
- feature flags
- data export/deletion
- backups
- production logging/monitoring
- security review
- rate limiting
- AI usage controls
- privacy controls

Production/security work that is required earlier should still be done in the slice that requires it; this slice is not an excuse to defer essential safeguards.
