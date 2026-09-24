# EdgeLog Status

Live status doc, kept up to date as work happens. Not a roadmap (see `ROADMAP.md`) and not a deploy how-to (see `DEPLOYMENT.md`) -- this is "what's actually true right now."

_Last updated: 2026-09-24_

## Standing rules (do not violate)

- **Never run anything that could wipe or destructively alter a database without taking a backup first.** `pg_dump` to `/var/backups/edgelog/` (or equivalent) before any migration, any manual DB surgery, or any command whose failure mode is data loss. This applies to dev and production alike.
- **Production (`/home/edgelog/app`, `edgelog-backend`, `edgelog.trade`) is off-limits unless explicitly told to deploy.** Dev/staging (`/home/edgelog/dev`, `edgelog-dev`, `d.edgelog.trade`) is where things get tested first.
- **Feature branch + PR for all changes**, merged into `main` (this session merges its own PRs directly now, per instruction -- no more waiting for manual merge). Production is deployed as its own separate, explicit step after `main` is in a good state.
- This session (GitHub-scoped Claude Code Remote) has **no SSH access** to `edgelog-prod`. A separate Claude Code Desktop session holds that; it currently only has `/home/edgelog/dev` in scope, not `/home/edgelog/app`.

## Where `main` is right now

`main` @ `4d31231` -- includes through PR #19. In order:

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

Three Alembic migrations exist beyond what's confirmed live in production: `004_trade_setups`, `005_trade_entries_and_cancel`, `006_trade_screenshot`. PR #18/#19 are app logic only, no new migrations.

## Vertical slices

- **VS1-VS3**: accepted, merged, built.
- **VS3 gaps** (from the original spec, not blocking): no `Draft` trade state (trades go straight to `Open`); no `reasoning`/`emotional state` per-trade fields (explicitly deferred by the user, not an oversight). R-multiple, the other original VS3/VS4 gap, **is now implemented** (client-side, via PR #19) -- no longer a gap.
- **VS4 -- Trade Calendar**: built in PR #19, per the user's explicit choice of "VS4 first" when a P&L/expenses dashboard was also requested. Verified end-to-end via Playwright in this session (multi-status trades, colors, R-multiple, drawer detail, both cross-links, week nav, mobile layout) but **not yet manually tested by the user in a live environment** -- treat as needing the same acceptance pass every prior slice got before calling it done.
- **Next planned slice (not started): P&L / expenses dashboard.** Prop-firm fees/payouts vs. trading profit, screenshot-upload-driven for now. Explicitly sequenced by the user to come after VS4. Nothing designed yet -- starts fresh when picked up.

## Deployment status

- **Dev (`d.edgelog.trade`)**: last confirmed deployed/tested through PR #15. **Not yet redeployed** with PR #16-#19 as of this update. (Note: the user was actively creating/editing trades including an `MNQZ26` one in a live environment earlier in this session -- unclear from this session whether that was dev or production, so don't assume either is caught up without checking.)
- **Production (`edgelog.trade`)**: a full deploy checklist (DB backup -> `pip install` -> `alembic upgrade head` -> set `ANTHROPIC_API_KEY` -> `el-deploy`) was handed off for the user to run manually, for the state as of PR #14. **Completion not confirmed in this session** -- no verification output has come back. Treat production as *not* confirmed up to date until that's checked, and now further behind main (#15-#19 on top of whatever did or didn't get deployed).

## Known open items

- Confirm whether the production deploy checklist was actually run, and if so, verify `edgelog.trade` matches `main`.
- Confirm which live environment (dev or prod) the user has been testing MNQZ26 trades on, and get it redeployed with PR #18 so those existing trades pick up correct dollar P&L (no migration needed -- it's computed fresh on every read).
- Deploy PR #16-#19 (collapsible add-contracts/add-trim; Target field move + trade screenshots; dated-contract multiplier fix; VS4 Trade Calendar) to dev, then production, once confirmed.
- VS4 needs the user's own manual acceptance pass on a real deployed environment -- this session's verification was Playwright-only, in a local sandbox.
- `el-deploy` (a shell function on the prod server) covers pull/install/migrate/restart/build/rsync/nginx-reload but does **not** back up the DB or set new env vars -- both must be done manually before calling it.
- Trade screenshot files are stored on local disk at `backend/uploads/trade_screenshots/` (gitignored, mirrors the existing bias-chart pattern) -- not included in the DB backup step, so a full disaster-recovery plan would need to back that directory up too if it matters long-term.

## Recent fixes worth remembering

- `greenlet` must stay pinned in `backend/requirements.txt` (PR #14) -- it's a transitive SQLAlchemy async dependency that silently drifted directly on the prod server before being committed properly.
- The Claude structured-output schema for screenshot extraction needs `anyOf`, not a multi-type array + `enum` together, for the `direction` field -- Anthropic's validator rejects the latter with a 400 (fixed in PR #11's update).
- A symbol typed/extracted with a dated-contract suffix (e.g. `MNQZ26`, `ESH25`) needs `get_multiplier()`'s root-stripping fallback (PR #18) to price correctly -- an exact-match-only lookup silently degrades to points-only P&L with no error.
