# Project onboarding and daily reorientation

## Purpose

Daily sync is an operational project handoff, not a request to summarize yesterday or write a status report. The goal is to equip this chat to work accurately on the application today: product behavior, architecture, development process, actual operations, current work, owner decisions and unresolved limits. A summary alone does not satisfy this task. Reading this protocol does not itself prove readiness.

## Required sequence

1. Establish repository identity, selected branch and fresh remote main SHA. For this project use **khammrich1/edgelog**, main. Do not equate the GitHub default branch, a remembered checkout or a feature branch with current main. Preserve working-tree changes; do not checkout/reset/pull over them during onboarding. When remote access is unavailable, disclose the exact limitation before relying on a local copy.
2. Read repository instructions, the sources below, application guide, development workflow, operational references and the latest EOD in full. Follow their authoritative links relevant to the current work. A directory listing or truncated excerpt is not reading the document. Continue through missing sections or mark coverage incomplete. Do not reconstruct a document from memory or search snippets.
3. Build the application model: its purpose, real user journey, principal components/data authorities, important failure paths, current scope and held work. Inspect the current code entry points/configuration relevant to the next task to distinguish intended design from actual implementation. Do not label documentation-only understanding as code/runtime verification. Full-app exhaustive audit is not required; identify the areas actually inspected.
4. Reconstruct the development process: issue authority, implementation branch/PR, reviewer/implementer roles, validation, exact candidate identity, DEV owner tests, failure loop, merge and production gates. Preserve project-specific workflow; do not replace it with a generic template.
5. Reconstruct operations from the latest detailed sources: environment names, domains, checkout paths, owning account, service/process, deployment helper and syntax, migration/backup side effects, logs, verification and recovery. Record unknown fields explicitly. A source may know more than a condensed guide. Before recommending a command, inspect the current relevant script/function evidence and authorization; do not guess syntax, service names or paths. A documented command is not permission to execute it.
6. Review the latest dated canonical status and all relevant EOD entries, current PR/issue state and accessible owner decisions since that handoff. Recheck referenced PRs/issues before describing their current state. Read relevant branch-only documentation/code for the active candidate and label it branch-only. Distinguish current task, completed behavior, accepted behavior, unresolved bugs and future scope.
7. Reconcile conflicts explicitly using the rules below. Read Todo for owner actions and the latest ProjectStatus update plus board for project gates; neither automatically overrides newer project/owner evidence. Do not resurrect completed or parked tasks. Do not treat a checked Todo box as proof of all product acceptance.
8. Return the onboarding receipt below. If an essential source or operational fact is missing, say exactly which area remains unknown; ask only for the missing information needed for the next action. Continue independent read-only work. Do not tell Kyle you are fully caught up while essential areas remain unread or conflicting.

## Project-specific understanding to demonstrate

Plan/trade/journal/reflection, local broker boundary, reconciliation stages, exact-PR DEV process, actual deploy wrapper side effects and production gate.

## Primary project sources

- [README.md](../README.md)
- [status.md](../status.md)
- [docs/DEVELOPMENT_WORKFLOW.md](../docs/DEVELOPMENT_WORKFLOW.md)
- [docs/ENVIRONMENT_REFERENCE.md](../docs/ENVIRONMENT_REFERENCE.md)
- [docs/DATA_FIRST_VERTICAL_SLICES_2026-10-13.md](../docs/DATA_FIRST_VERTICAL_SLICES_2026-10-13.md)

Also read [APPLICATION_GUIDE.md](APPLICATION_GUIDE.md), [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md), [RUNBOOK.md](RUNBOOK.md), [EOD_STATUS.md](../EOD_STATUS.md) and [DAILY-SYNC.md](../DAILY-SYNC.md). These orientation guides are secondary indexes, not a substitute for the detailed authorities above. Follow operational and feature links as needed.

## Conflict and freshness rules

- Latest explicit owner instruction governs task scope. Respect repository safety/acceptance boundaries unless that instruction explicitly changes them.
- Compare evidence at the level of the specific claim, including event date and revision. A newly created summary can repeat old facts; its file timestamp does not make those facts current.
- A current detailed operational source or direct operator evidence supersedes a generic guide's stale claim that the fact is unknown. State discrepancies instead of repeating both as current truth.
- Historical EOD, audits and daily snapshots describe their recorded date. Do not execute their old next actions without reconciliation. Preserve valid owner passes and held scope.
- Separate design intent, code inspected, tests reported, tests independently checked, merged, deployed and owner accepted. Main SHA is not running-service identity. Checkout identity is not frontend asset identity.
- If equally authoritative sources conflict without resolving evidence, name the conflict and the narrow next verification. Do not silently select a command or make up the missing fact.
- If new owner information arrives after onboarding, reconcile it immediately. Before an operational command or implementation handoff, recheck the relevant source and candidate freshness; a morning receipt is not permanent validation.

## Onboarding receipt - required user-facing result

Keep it concise, but cover each item with concrete facts and source links:

1. **Identity and coverage:** repo, branch, main SHA, Pacific check time; exact documents/code/PRs read and inaccessible sources. Cite relevant headings/lines or immutable file/commit links, not just a file list.
2. **Application understanding:** explain the real user flow and the components/data authorities involved in today's task. Mark intended versus implemented versus runtime-verified behavior.
3. **How we develop:** state this project's actual issue-to-owner-test-to-release sequence and roles, including DEV and production gates.
4. **How we operate:** report verified environment/path/service/helper facts relevant to today's task, command side effects, logs/recovery references and unresolved fields. Do not offer a deploy command when its target or syntax is unknown.
5. **Current work and decisions:** current issue/PR and exact candidate, latest owner PASS/FAIL, blockers, completed/parked work to preserve. State which claims were checked live and which are carried forward.
6. **Corrections:** old versus current conflicting instructions, with evidence and what will be followed. If none found, state the coverage inspected rather than claiming no conflicts exist anywhere.
7. **Next step and limits:** up to three priorities and a concrete first action within authorization. Explicitly identify incomplete onboarding areas; readiness applies only to the supported next task. Do not end with a bare 'synced', 'good to go' or 'caught up'.

The receipt demonstrates understanding; it does not authorize feature work, external messages, deployment, simulations, trades or database changes. Do not execute mutations just to prove understanding.

## Saving the handoff

After reconciliation, append a timestamped receipt/evidence summary to DAILY-SYNC.md while preserving previous history. Update its current orientation only from supported facts. Publish reporting-only changes directly to fresh main under the owner's daily reporting instruction, preserving concurrent work and normal product release gates. Do not mix feature commits into reporting, force-push or bypass protections. Report an unpublished receipt as unpublished. Do not invent yesterday's accomplishments. Updating Todo/ProjectStatus across projects is a separate coordination action, not a prerequisite for understanding this application.

## Document roles and existing setup

Use [PROJECT_DOCUMENTS.md](PROJECT_DOCUMENTS.md) for each document's job. Read [APPLICATION_SETUP.md](APPLICATION_SETUP.md) and its existing detailed sources before giving setup/deploy instructions. EOD summarizes the day; daily sync orients this chat to work. Do not confuse one with the other or invent a second workflow/setup source when the repo already documents it.
