# EdgeLog - Operations runbook

Detailed authority: [ENVIRONMENT_REFERENCE.md](ENVIRONMENT_REFERENCE.md); delivery order: [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md).

1. Confirm DEV d.edgelog.trade versus PROD edgelog.trade and inspect actual wrapper/service mapping using the read-only checks in ENVIRONMENT_REFERENCE.md. A checkout SHA alone does not prove service identity.

2. For an authorized exact-PR DEV deployment the documented wrapper is `dev-el-deploy pr <PR_NUMBER>`.

3. After owner PASS and authorized merge, separately approved production uses `el-deploy`. Do not replace wrappers with generic git pull/restart.

Verification: record deployed SHA, environment, relevant endpoint/UI evidence and owner results. Reconciliation preview acceptance remains read-only; no broker writes, imports, history mutation or live orders are implied.

Recovery/rollback: real wrapper-supported rollback, service mapping and log locations remain verification gaps in ENVIRONMENT_REFERENCE.md. Obtain operator evidence before recovery; preserve broker/journal data rather than changing financial rows to hide an anomaly.

Update the environment reference when runtime facts are verified. Record paths/identifiers only; never publish credentials or .env values.

Record verified operations in canonical status and [EOD_STATUS.md](../EOD_STATUS.md).
