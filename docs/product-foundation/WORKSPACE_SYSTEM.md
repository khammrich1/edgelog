# Workspace System - P3.5 Owner Revision

Baseline: #41 / #50, owner-selected PR #49 merged October 7, 2026.
The October 8 visual follow-up is scoped by #51 and awaits its own DEV acceptance.
See [visual polish evidence](../SITE_IMPROVEMENTS_2026-10-08.md).

## Shared Rules

- Canvas: `--el-bg`; structural rail uses a quieter graphite plane.
- Framed data-entry forms: `form.el-workstation` on `--el-surface`.
- Ordinary sections: unframed `.el-workstation` with a top divider.
- Hover/selected surfaces: `--el-surface-raised`; copper identifies the active
  navigation item, primary command, and focus. Green/red retain existing
  financial and direction semantics.
- Labels use shared tokens with readable contrast. Compact page titles are
  24-26px; body/control text is 14-16px. No promotional hero on working screens.
- Desktop sidebar stays within the viewport. Mobile uses an explicit menu
  rather than an overflowing horizontal navigation strip.
- Dashboard retains Today | This Week, then keyboard-accessible recent days.
- Daily Journal retains Mood & Bias | Trades | Overview and the full trade
  ticket. The datetime field spans two grid tracks to avoid truncation.
- Calendar and history fetches distinguish loading, failure, and empty data.
- Stats is still a placeholder; this revision is not analytics delivery.

## Verification Evidence

The images use synthetic data in a temporary local preview, not the owner's
account. The preview fixture was removed before commit. Desktop viewport
1280px, mobile 390px. Checked page scroll width against viewport width on
Dashboard, Daily Journal, Calendar, and Trades; no page overflow observed.
Checked mobile navigation open/dismiss, daily tabs and selected-day history.
No live save/delete or financial action was performed.

- [Dashboard desktop](screenshots/p35-rebuild/dashboard-desktop.jpg)
- [Journal desktop](screenshots/p35-rebuild/journal-desktop.jpg)
- [Dashboard mobile](screenshots/p35-rebuild/dashboard-mobile.jpg)
- [Full trade ticket mobile](screenshots/p35-rebuild/trade-ticket-mobile.jpg)

Frontend regression suite: 200 tests passing; production build passing.
Exact PR DEV deployment and owner PASS remain required before merge.
