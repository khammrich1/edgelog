# edgelog - Project onboarding and daily sync

## What these documents do

**EOD summarizes the day. Daily Sync gets this chat up to speed on the project and ready to work. Development Workflow records the current development process. Application Setup preserves the existing setup and operational knowledge.** Read [the source map](docs/PROJECT_DOCUMENTS.md) and [Application Setup](docs/APPLICATION_SETUP.md); follow the existing detailed sources rather than recreating their instructions.


## Run this in the project chat

> Onboard yourself to this project for today's work, not just its status. Read docs/DAILY_SYNC_PROTOCOL.md on fresh main and follow it. Learn how the application actually works, how we develop it, how we operate it, the active work and my latest decisions. Reconcile conflicting/old instructions against current evidence. Return the required onboarding receipt with sources/revisions, application understanding, development workflow, verified operational facts, current gate, corrections and remaining gaps before saying you are ready. Do not execute implementation or operational changes as part of onboarding. Preserve the dated handoff history.

Read [the full onboarding protocol](docs/DAILY_SYNC_PROTOCOL.md). Read the detailed authorities it links; the three orientation guides are entry points, not complete verified manuals. A status summary or acknowledgment does not complete this sync.

## Historical handoff - not current instructions

The preserved material below records an earlier handoff. Its priorities, missing facts and PR states must be reconciled before use. Do not repeat them as current guidance merely because they are in this file.


Sync date: 2026-10-20 (America/Los_Angeles)
Reporting window: 2026-10-19 (previous Pacific calendar day)
Repository: khammrich1/edgelog, branch main
Canonical project status: [status.md](status.md)
Yesterday's handoff: [EOD_STATUS.md](EOD_STATUS.md)

## Project focus

Read-only reconciliation preview, DEV evidence, actual fee/commission semantics and unresolved P&L. Preserve separation of broker identity, fill grouping and plan association; no live trades or imports.

## Daily history

### 2026-10-20 - Morning handoff from October 19

Evidence basis: the published October 19 EOD entries reviewed for this project. This entry summarizes yesterday's recorded work, not a fresh code, runtime, deployment or owner-acceptance audit. Historical test claims remain attributed to the EOD source. No new product progress is claimed by creating this file.

#### Yesterday's recorded completions

- Reviewed PR #91 follow-up against approved grouping and plan-association rules — October 19; stage: code review only, no owner acceptance; evidence: https://github.com/khammrich1/edgelog/pull/91 . Claude reported fixes and 207 tests passing, not independently rerun here.
- Reviewed PR #85's test-only P&L investigation and requested order-independent assertions — October 19; stage: review feedback, not merge; evidence: https://github.com/khammrich1/edgelog/pull/85#issuecomment-6276621143 .
- Verified PR #93's standard EOD workflow documentation is merged — verified October 19, merge date not independently established in this snapshot; stage: merged; evidence: https://github.com/khammrich1/edgelog/pull/93 .

- Verified prior EOD reporting [PR #94](https://github.com/khammrich1/edgelog/pull/94) merged to main — verified October 19; stage: merged documentation only; exact merge time not established in this snapshot.
- Read and applied the revised EOD workflow allowing direct documentation commits to main — October 19; stage: reporting process only; evidence: [docs/PROJECT_EOD_UPDATE.md](docs/PROJECT_EOD_UPDATE.md).

#### Current state carried forward

EdgeLog's journal remains the working product; commission/fee/net-P&L work (#81) is merged, with exact PROD deployment unverified. Broker diagnostic, account selection, B/E action and Step 3A reconciliation preview remain in open draft PRs, not production-verified features. The canonical status has been refreshed with this follow-up.

#### Unresolved blockers carried forward

- DEV deployed SHA and synthetic endpoint acceptance evidence missing — blocks PR #91 approval; responsible: Claude/DEV operator; next unblock action: confirm branch/revision, run read-only checks, post results; follow-up: next work session; evidence: PR #91.
- Reliable entry/exit pairing across broker order IDs not yet proven — blocks verified automatic completed-trade P&L; responsible: development; next unblock action: keep unresolved until deterministic position-transition evidence is available; follow-up: subsequent scoped work; evidence: PR #91.
- Broker `fees` and `commissions` relationship unverified against statement — blocks safe net-cost import; responsible: Kyle/development; next unblock action: reconcile raw values with real statement; follow-up: before write/import; evidence: issue #80.
- Original #62 -$19,884 anomaly unexplained — blocks claiming incident fixed; responsible: development/Kyle; next unblock action: inspect actual persisted rows/API response if reproducible; follow-up: next review; evidence: PR #85.

#### Next actions carried forward

1. Claude/DEV operator: deploy PR #91 to DEV only after verifying revision, run throwaway-account acceptance tests and post SHA/results; due: next work session.
2. Nova/Kyle: review acceptance evidence and obtain explicit owner PASS before any PR #91 merge; due: after tests.
3. Claude/Kyle: finish #85 review and compare real TopstepX fee statement; due: unscheduled.

#### Kyle's input carried forward

- Owner PASS after verified #91 DEV evidence and a real TopstepX statement for fee/commission correlation; no additional access needed for synthetic DEV checks if Claude has DEV access.

#### First action

Review the carried-forward next actions against today's owner priorities before starting work. Resolve the first blocking evidence or decision within the existing scope.

#### Coverage and coordination

- Source: [October 19 EOD record](EOD_STATUS.md), including earlier entries when the latest entry is incremental.
- Project-specific authority: [status.md](status.md).
- Shared actions: [Todo](https://github.com/khammrich1/Todo/blob/main/README.md).
- Shared project gates: [ProjectStatus reconciliation](https://github.com/khammrich1/ProjectStatus/blob/main/updates/2026-10-19-sync.md).
- EOD history and canonical status remain authoritative; this file is the start-of-day handoff.
- No implementation, test run, deployment, account action, or cross-project task/status mutation performed by this documentation update.
