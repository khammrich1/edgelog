# EdgeLog Status

Live status doc, kept up to date as work happens. Not a roadmap (see `ROADMAP.md`) and not a deploy how-to (see `DEPLOYMENT.md`) -- this is "what's actually true right now."

_Last updated: 2026-09-21_

## Standing rules (do not violate)

- **Never run anything that could wipe or destructively alter a database without taking a backup first.** `pg_dump` to `/var/backups/edgelog/` (or equivalent) before any migration, any manual DB surgery, or any command whose failure mode is data loss. This applies to dev and production alike.
- **Production (`/home/edgelog/app`, `edgelog-backend`, `edgelog.trade`) is off-limits unless explicitly told to deploy.** Dev/staging (`/home/edgelog/dev`, `edgelog-dev`, `d.edgelog.trade`) is where things get tested first.
- **Feature branch + PR for all changes**, merged into `main` (this session merges its own PRs directly now, per instruction -- no more waiting for manual merge). Production is deployed as its own separate, explicit step after `main` is in a good state.
- This session (GitHub-scoped Claude Code Remote) has **no SSH access** to `edgelog-prod`. A separate Claude Code Desktop session holds that; it currently only has `/home/edgelog/dev` in scope, not `/home/edgelog/app`.

## Where `main` is right now

`main` @ `cfa1c3f` -- includes through PR #16. In order:

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

Two Alembic migrations exist beyond what's confirmed live in production: `004_trade_setups`, `005_trade_entries_and_cancel`.

## Deployment status

- **Dev (`d.edgelog.trade`)**: has been deployed to and manually tested multiple times through PR #15 (target-hit, browse button, green/red colors all verified live there per that PR's description). **Not yet redeployed** with PR #16's collapsible-forms change as of this update.
- **Production (`edgelog.trade`)**: a full deploy checklist (DB backup -> `pip install` -> `alembic upgrade head` -> set `ANTHROPIC_API_KEY` -> `el-deploy`) was handed off for the user to run manually. **Completion not confirmed in this session** -- no verification output has come back. Treat production as *not* confirmed up to date until that's checked.

## Known open items

- Confirm whether the production deploy checklist was actually run, and if so, verify `edgelog.trade` matches `main`.
- Deploy PR #16 (collapsible add-contracts/add-trim) to dev, then production, once confirmed.
- `el-deploy` (a shell function on the prod server) covers pull/install/migrate/restart/build/rsync/nginx-reload but does **not** back up the DB or set new env vars -- both must be done manually before calling it.

## Recent fixes worth remembering

- `greenlet` must stay pinned in `backend/requirements.txt` (PR #14) -- it's a transitive SQLAlchemy async dependency that silently drifted directly on the prod server before being committed properly.
- The Claude structured-output schema for screenshot extraction needs `anyOf`, not a multi-type array + `enum` together, for the `direction` field -- Anthropic's validator rejects the latter with a 400 (fixed in PR #11's update).
