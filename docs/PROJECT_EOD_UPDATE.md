# Standard project EOD status workflow

Give this file to each project chat and say:

> Update the project status and append a dated entry to EOD_STATUS.md using this standard.

## Standard document

Every project uses one file at the repository root: `EOD_STATUS.md`.

- Create it from the local [EOD entry template](EOD_STATUS_TEMPLATE.md) on first use, replacing placeholders with project facts.
- Append each new entry at the bottom, under `## YYYY-MM-DD — HH:mm PT`.
- Use America/Los_Angeles dates and times. Include an ISO timestamp with its UTC offset in every entry.
- Each entry is a complete snapshot of current status, with that date's progress, blockers, and next actions.
- Preserve all previous entries. For another update the same day, append a new timestamped entry with only newly completed work in its completion list. Label corrections explicitly and reference the entry corrected.
- Do not create separate daily files. Keep the existing canonical status document current and link it to `EOD_STATUS.md`; the EOD file is the chronological history.

## Instructions for each project chat

1. Read repository instructions and the existing canonical status document. Known locations: FitRetro_v2 and edgelog use `status.md`; ownerit and breach-vector use `docs/CURRENT_STATUS.md`; Airlock uses the README status section with `docs/ACCEPTANCE.md` and `docs/ROADMAP.md`; BeforeWeMeet uses `ROADMAP.md`; Today uses `docs/ROADMAP.md`. Preserve these existing authorities.
2. Review this session, working-tree changes, commits, relevant PRs/issues, actual test results, deployment evidence, and Kyle's decisions or acceptance reports. Record inaccessible evidence as not verified.
3. Update the canonical status document in place: current state, milestone/gate, blockers, and next actions. Preserve owner wording, scope boundaries, parked work, and prior acceptance unless explicitly superseded.
4. Append the standard entry to root `EOD_STATUS.md`. Use the format in the local [EOD entry template](EOD_STATUS_TEMPLATE.md). Replace every placeholder; use `None recorded` or `Not verified` when appropriate. Record when completed events happened, especially across midnight, so the daily sync can assign them to the correct day.
5. Record blockers explicitly, including what is blocked, who can resolve it, and the next unblock action. Carry unresolved blockers into each current snapshot; list resolved blockers separately.
6. Keep implemented, tested, merged, deployed, and owner-accepted states separate. A merge, passing build, or missing task does not establish owner acceptance or completion on a particular date.
7. Follow the project's normal commit/PR workflow. Do not merge implementation work or deploy as part of reporting. Return the status-file path, EOD path, branch, and commit/PR link. Clearly identify unpushed/local-only changes; GitHub-based sync cannot read them.
8. Report completed work, current blockers, next action, and any specific input needed from Kyle. Do not claim publication unless verified.

## Daily sync in the Today chat

When Kyle says `Run the daily sync`:

1. Review each project's `EOD_STATUS.md` and canonical status document. Use the latest dated snapshot for current state; use individual event dates for yesterday's completions. Check relevant published PR branches and label branch-only work.
2. Cross-check changed commits, PRs, issues, and available deployment evidence since the previous successful sync. Flag stale, conflicting, missing, or unpublished records rather than inventing progress.
3. Use the previous Pacific calendar day for yesterday's results. Avoid counting an accomplishment twice when repeated in later snapshots. Keep today's activity separate.
4. Update the matching ProjectStatus board and README table together, preserving history and evidence links.
5. Reconcile actionable owner tasks into Todo, respecting explicit priorities, completed tasks, and parked work. Project next actions are candidates for the overall top three.
6. Refresh Today after updating the sources and report coverage and unresolved evidence gaps.

The current Today app does not automatically read project EOD files. Until that integration is implemented, the assistant running the daily sync reviews them and updates ProjectStatus explicitly. This standard does not itself schedule a job. Ask the project chat to run the EOD update; merely installing this document does not trigger one.
