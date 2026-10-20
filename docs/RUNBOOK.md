# EdgeLog - Operations runbook

> Orientation source, not a live-state certificate. Follow [DAILY_SYNC_PROTOCOL.md](DAILY_SYNC_PROTOCOL.md) and the current detailed authorities linked below. Reconcile each claim by its evidence date/revision; do not repeat this guide's unknowns when a newer detailed source has resolved them.


Detailed authority: [ENVIRONMENT_REFERENCE.md](ENVIRONMENT_REFERENCE.md); delivery order: [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md).

1. Confirm DEV d.edgelog.trade versus PROD edgelog.trade and inspect actual wrapper/service mapping using the read-only checks in ENVIRONMENT_REFERENCE.md. A checkout SHA alone does not prove service identity.

2. For an authorized exact-PR DEV deployment the documented wrapper is `dev-el-deploy pr <PR_NUMBER>`.

3. After owner PASS and authorized merge, separately approved production uses `el-deploy`. Do not replace wrappers with generic git pull/restart.

Verification: record deployed SHA, environment, relevant endpoint/UI evidence and owner results. Reconciliation preview acceptance remains read-only; no broker writes, imports, history mutation or live orders are implied.

Recovery/rollback: read the current ENVIRONMENT_REFERENCE.md for the verified wrapper bodies, service/checkout mapping and remaining recovery gaps. Some wrappers reset DEV work, apply Alembic migrations and rsync with --delete; inspect that evidence and the target before recommending execution. Do not describe all wrapper/service/log facts as unknown merely because this orientation guide originally lacked them. Confirm an actual rollback/restore procedure separately; preserve broker and journal data.

Update the environment reference when runtime facts are verified. Record paths/identifiers only; never publish credentials or .env values.

Record verified operations in canonical status and [EOD_STATUS.md](../EOD_STATUS.md).