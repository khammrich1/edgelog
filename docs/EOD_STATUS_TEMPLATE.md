# <Project name> — EOD Status

Repository: <owner/repository>
Canonical status document: <relative Markdown link>
Timezone: America/Los_Angeles

Append new dated entries at the bottom. Preserve prior entries. The latest entry is the current snapshot; completion dates determine which day's accomplishments an item belongs to.

---

## YYYY-MM-DD — HH:mm PT

Recorded at: <ISO timestamp with Pacific UTC offset>
Evidence reviewed: <branch, implementation commit SHA, PR/issue links, test/deployment records>
Coverage: <period reviewed and any inaccessible sources>

### Current project status

<Concise current product state. Distinguish verified facts, owner reports, and unknowns.>

### Current milestone / next gate

<Milestone, acceptance criteria, and what remains before advancing.>

### Completed on this date

- <Newly completed outcome> — completed <event date/time>; stage: <implemented/merged/deployed/owner-accepted>; evidence: <link/reference>.

### In progress

- <Work item> — remaining work: <details>; location: <branch/PR/local-only>.

### Current blockers

- <Blocker> — blocks: <outcome>; responsible party: <name/unknown>; next unblock action: <action>; follow-up: <date/unscheduled>; evidence: <reference>.

### Blockers resolved on this date

- <Blocker> — resolved <event date/time>; resolution and evidence: <details>.

### Verification and delivery

- Implemented: <scope + evidence, or not verified>.
- Tests: <checks actually run, results, and gaps>.
- Merged: <PR/commit, or not merged/not verified>.
- Deployed: <environment + revision + evidence, or not verified>.
- Owner accepted: <explicit result + date, or awaiting acceptance>.

### Decisions / scope boundaries

- <Decision and source; preserve stop lines and parked work>.

### Next actions

1. <Concrete action> — responsible party: <name/unknown>; due: <date/none>.
2. <Action if needed>.
3. <Action if needed>.

### Kyle's input needed

- <Specific test, decision, access, or offline result needed; or none>.

### Publication / handoff

- Status update location: <main branch link; return the resulting commit URL in the handoff, or explicitly report unpublished changes>. No EOD-only PR.
- Remaining evidence gaps: <details, or none>.

### Ticket reconciliation

| Issue / PR | Published update and resulting state | Evidence / comment URL | Remaining gate / next action |
| --- | --- | --- | --- |
| Fill with actual affected tickets; use None affected only after checking | Record verified mutations or already-current/no-change | Link actual evidence, not proposed text | Record incomplete/blocked work explicitly |

Ticket reconciliation coverage: Complete / Partially complete (explain failures or missing acceptance evidence). Verify writes before reporting completion; avoid duplicate comments. The template describes fields to fill, not proof that an update occurred.
