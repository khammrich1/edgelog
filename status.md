# EdgeLog Status

Live status doc, kept up to date as work happens. Not a roadmap (see `ROADMAP.md`) and not a deploy how-to (see `DEPLOYMENT.md`) -- this is "what's actually true right now."

_Last updated: 2026-09-24 (PR #23)_

## Standing rules (do not violate)

- **Never run anything that could wipe or destructively alter a database without taking a backup first.** `pg_dump` to `/var/backups/edgelog/` (or equivalent) before any migration, any manual DB surgery, or any command whose failure mode is data loss. This applies to dev and production alike.
- **Production (`/home/edgelog/app`, `edgelog-backend`, `edgelog.trade`) is off-limits unless explicitly told to deploy.** Dev/staging (`/home/edgelog/dev`, `edgelog-dev`, `d.edgelog.trade`) is where things get tested first.
- **Feature branch + PR for all changes**, merged into `main` (this session merges its own PRs directly now, per instruction -- no more waiting for manual merge). Production is deployed as its own separate, explicit step after `main` is in a good state.
- This session (GitHub-scoped Claude Code Remote) has **no SSH access** to `edgelog-prod`. A separate Claude Code Desktop session holds that; it currently only has `/home/edgelog/dev` in scope, not `/home/edgelog/app`.

## Where `main` is right now

`main` @ `3306212` -- includes through PR #23. In order:

| PR | What it added |
|---|---|
| #9 | VS3 Trade Lifecycle (create/trim/close, P&L, planned risk) |
| #10 | Symbol dropdown (MNQ/MES/MGC/MCL) + custom entry |
| #11 | AI screenshot trade capture (Claude vision), configurable trade setups, cancel/scale-in/stop-hit, nav |
| #12 | Journal Day tabs (Mood & Bias / Trades / Overview), Long/Short toggle, Price/Points stop & target, R:R preview, trade cards, editable trims/edit-trade |
| #13 | Merged the #11/#12 stack (which had been built on top of each other, not on `main`) into `main` |
| #14 | Pinned `greenlet==3.1.1` (was drifted directly onto the prod server outside git) |
| #15 | Target-hit shortcut, screenshot dropzone "browse a file" button, LONG/SHORT switched to green/red (explicit request, reversing the earlier copper/steel-only direction rule) |
| #16 | Add-contracts/add-trim collapsed behind "+ Add contracts" / "+ Add trim" toggle buttons instead of always-visible |
| #17 | Target moved onto the primary trade form row (was behind "More fields"); trades can now store an actual setup screenshot image (`trades.screenshot_path`, migration `006`, upload/get/delete endpoints), auto-attached from the AI dropzone or added/replaced/removed per-trade at any time |
| #18 | Fixed dated futures contracts (e.g. `MNQZ26`) falling back to points-only P&L/risk instead of resolving to their root's dollar multiplier (`MNQ`) |
| #19 | **VS4 -- Trade Calendar**: new `/trades` weekly view, separate from the Daily Journal calendar. New `GET /journal/trades?start=&end=` range endpoint, collapsed/expanded trade cards, client-side R-multiple, mobile day-focused view. See "Vertical slices" below. |
| #20 | **Annual P&L / Financial Tracker**: new standalone `/financials` + `/financials/:year` views -- a flat cash ledger of prop-firm business expenses (evals, deposits) vs. income (payouts), deliberately separate from Trade/TradingDay P&L. New `FinancialEntry` model/migration `007`, `/financial-entries` CRUD + range-query + screenshot API, `/financial-entries/parse-screenshot` AI-capture endpoint (same extraction-only-prefills pattern as trades). Monthly bar chart (green income / steel-gray expenses, not red), entries table, year navigation via `replace`. See "Vertical slices" below. |
| #21 | **Bulk screenshot import for the Financial Tracker**: a real TopStep payout-history screenshot (multiple finalized payouts in one table) showed the single-entry AI capture can only extract one row per image. Added a separate, opt-in "Import multiple from a screenshot" panel (collapsed by default) -- new `/financial-entries/parse-screenshot-bulk` endpoint returns a list of candidate rows, new `/financial-entries/bulk` endpoint creates them all in one all-or-nothing request. Extraction results render as an editable, per-row-includable review table; nothing saves until the user reviews and submits, matching the single-entry flow's never-auto-save rule. No new migration. |
| #22 | **Financial capture prompt fix**: first live test of PR #21 against the real Anthropic API (TopStep payout-history screenshot) correctly extracted all rows, but put the raw account ID (`EXPRESS-V2-CT-...`) in the `firm` field instead of the actual firm/brand name (`TopStep`) shown in the page header. Tightened both the single-entry and bulk extraction prompts: `firm` must be the firm's own brand name, never an account number -- an account ID goes to `notes` instead. Prompt-only change. |
| #23 | **Bulk-import duplicate detection + zero-amount entries**: two follow-ups from continued live testing. (1) Re-importing a payout screenshot that overlaps with entries already in the ledger had no duplicate protection -- `parse-screenshot-bulk` now flags a row as `possible_duplicate` when an existing entry matches its date+amount+category, and the review table starts those rows unchecked (still re-checkable). (2) `amount` required a strictly-positive value, so a $0.00 row (e.g. a free reset) failed validation and broke the whole all-or-nothing batch -- relaxed to allow zero, rejecting only negative amounts, so resets/comped items can be logged and counted. |

Four Alembic migrations exist beyond what's confirmed live in production: `004_trade_setups`, `005_trade_entries_and_cancel`, `006_trade_screenshot`, `007_financial_entries`. PR #18/#19/#21/#22/#23 are app logic only, no new migrations.

## Vertical slices

- **VS1-VS3**: accepted, merged, built.
- **VS3 gaps** (from the original spec, not blocking): no `Draft` trade state (trades go straight to `Open`); no `reasoning`/`emotional state` per-trade fields (explicitly deferred by the user, not an oversight). R-multiple, the other original VS3/VS4 gap, **is now implemented** (client-side, via PR #19) -- no longer a gap.
- **VS4 -- Trade Calendar**: built in PR #19, per the user's explicit choice of "VS4 first" when a P&L/expenses dashboard was also requested. Verified end-to-end via Playwright in this session (multi-status trades, colors, R-multiple, drawer detail, both cross-links, week nav, mobile layout) but **not yet manually tested by the user in a live environment** -- treat as needing the same acceptance pass every prior slice got before calling it done.
- **Annual P&L / Financial Tracker**: built in PR #20, the P&L/expenses dashboard sequenced after VS4. Scope was deliberately kept lean at the user's request ("get me something to work with and I will go from there"): single flat ledger, free-text category, both manual and AI-screenshot entry, no multi-account model/multi-currency/recurring entries/budgets/CSV import-export. Verified end-to-end via Playwright in this session (entry CRUD, year nav via `replace`, cross-year date edits, chart colors/tooltip, screenshot dropzone graceful fallback, 400px layout) but **not yet manually tested by the user in a live environment**.
- **Bulk screenshot import**: built in PR #21, a follow-up the user asked for immediately after seeing PR #20 -- their real payout screenshots are multi-row tables, not single entries. See "Where `main` is right now" above for what it does. Verified via curl against both new endpoints in this session (couldn't verify real multi-row AI extraction end-to-end here -- no `ANTHROPIC_API_KEY` in this sandbox, only the graceful-503 fallback path) plus a live Playwright pass on the toggle/panel UI. **The user then tested it live against the real Anthropic API once deployed** and it correctly extracted a real 6-row TopStep payout table -- confirmed working end-to-end. Two issues surfaced from that live use, both fixed same-day: the firm-name/account-ID mixup (PR #22) and duplicate-import risk + zero-amount rejection (PR #23, see above).
- **No further slice queued yet** -- pick up with the user next.

## Deployment status

- **Somewhere live (dev or prod -- this session can't tell which) is running through at least PR #21**: the user tested bulk import live against the real Anthropic API and got a correct 6-row extraction, which is only possible with PR #21 deployed. **PR #22 and #23 (this session's same-day follow-up fixes) have NOT been confirmed deployed anywhere yet** -- the firm-name/account-ID bug and the zero-amount/duplicate-import gaps are still live in production/dev until that environment is redeployed again.
- **Production (`edgelog.trade`)**: a full deploy checklist (DB backup -> `pip install` -> `alembic upgrade head` -> set `ANTHROPIC_API_KEY` -> `el-deploy`) was handed off for the user to run manually, for the state as of PR #14, and clearly has been run at least once more since then given the above. Exact current commit on each of dev/production is still **not confirmed from this session** -- this session has no SSH access to verify directly (see standing rules).

## Known open items

- **Immediate**: get PR #22 and #23 deployed (firm-name fix + duplicate detection + zero-amount) to wherever the user is actively using the app -- these are live-bug fixes for a feature already in active use, not queued backlog.
- Confirm which environment(s) (dev, prod, or both) are actually running which PR -- this session can only infer from user reports, not check directly.
- Confirm which live environment (dev or prod) the user has been testing MNQZ26 trades on, and get it redeployed with PR #18 so those existing trades pick up correct dollar P&L (no migration needed -- it's computed fresh on every read).
- PR #20 adds migration `007_financial_entries` -- back up the DB before running `alembic upgrade head` on any environment not yet caught up to it, per the standing rule above. PRs #18/#19/#21/#22/#23 add no migrations.
- VS4 (Trade Calendar) still needs the user's own manual acceptance pass on a real deployed environment -- unlike the Financial Tracker/bulk import, no live user feedback on it yet.
- The Trade Calendar has no per-day trade-count/total-P&L summary -- the user asked for one after mistaking the Daily Journal calendar's checklist-progress badge ("0/1") for a trade counter. Proposed fix (not yet built, not yet approved by the user): add a count + total P&L to each day column on `/trades`. Waiting on the user before starting.
- `el-deploy` (a shell function on the prod server) covers pull/install/migrate/restart/build/rsync/nginx-reload but does **not** back up the DB or set new env vars -- both must be done manually before calling it.
- Trade screenshot files are stored on local disk at `backend/uploads/trade_screenshots/` (gitignored, mirrors the existing bias-chart pattern) -- not included in the DB backup step, so a full disaster-recovery plan would need to back that directory up too if it matters long-term. The Financial Tracker's screenshots at `backend/uploads/financial_screenshots/` have the exact same gap.

## Recent fixes worth remembering

- `greenlet` must stay pinned in `backend/requirements.txt` (PR #14) -- it's a transitive SQLAlchemy async dependency that silently drifted directly on the prod server before being committed properly.
- The Claude structured-output schema for screenshot extraction needs `anyOf`, not a multi-type array + `enum` together, for the `direction` field -- Anthropic's validator rejects the latter with a 400 (fixed in PR #11's update).
- A symbol typed/extracted with a dated-contract suffix (e.g. `MNQZ26`, `ESH25`) needs `get_multiplier()`'s root-stripping fallback (PR #18) to price correctly -- an exact-match-only lookup silently degrades to points-only P&L with no error.
- A vague extraction-prompt field description (e.g. "account name") will make Claude pick up the nearest matching row text (an account ID) instead of the actually-wanted value (the firm's brand name from page branding) -- be explicit about what a field is NOT, not just what it is (PR #22).
- All-or-nothing batch validation (bulk-create) means a single edge-case row (e.g. a legitimate $0.00 entry that used to be rejected as non-positive) silently blocks the entire batch with no partial success -- worth remembering as a sharp edge any time a new bulk-anything endpoint is added (PR #23).
